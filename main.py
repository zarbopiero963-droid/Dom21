import sys
import os
import subprocess
import glob
import logging
import multiprocessing

from core.utils import resource_path

# 🛡️ BOOTSTRAPPER LTM (Long Term Maintainable)
app_data = os.getenv('LOCALAPPDATA', os.path.expanduser('~'))
browser_path = os.path.join(app_data, "SuperAgent_Browsers")
os.environ["PLAYWRIGHT_BROWSERS_PATH"] = browser_path

# --- HACK PYINSTALLER PER I PERCORSI DEI MODULI ---
# Quando eseguito come .exe, aggiungi la cartella temporanea _MEI al sys.path
if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
    sys.path.insert(0, sys._MEIPASS)
else:
    # Se eseguito come script, aggiungi la root del progetto
    sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))


def ensure_playwright_browsers(logger):
    """
    Verifica l'esistenza REALE dell'eseguibile Chromium.
    Se mancante o corrotto, tenta il download silenzioso e logga i fallimenti.
    """
    if getattr(sys, 'frozen', False):
        # Cerca l'eseguibile fisico, non solo la cartella (supporta Win e Linux)
        chrome_execs = glob.glob(os.path.join(browser_path, "chromium-*", "chrome-win", "chrome.exe")) + \
                       glob.glob(os.path.join(browser_path, "chromium-*", "chrome-linux", "chrome"))
        
        if not chrome_execs:
            logger.warning("⚙️ Bootstrap: Browser Chromium non trovato o corrotto. Inizio download silente...")
            try:
                from playwright._impl._driver import compute_driver_executable, get_driver_env
                driver_executable = compute_driver_executable()
                env = get_driver_env()
                
                creation_flags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
                
                # Check=True per forzare l'eccezione in caso di download fallito/troncato
                subprocess.run(
                    [driver_executable, "install", "chromium"], 
                    env=env, 
                    creationflags=creation_flags,
                    check=True,
                    capture_output=True
                )
                logger.info("✅ Bootstrap: Browser Chromium installato con successo.")
            except Exception as e:
                logger.critical(f"❌ ERRORE Bootstrap Browser: Impossibile scaricare Chromium. Errore: {e}")
                # Lasciamo proseguire l'app (check=False logico), la UI si aprirà ma il Worker fallirà in modo sicuro

# Spostiamo l'import dell'app QUI, DOPO aver sistemato sys.path
from PySide6.QtWidgets import QApplication

# Importiamo esplicitamente tutti i tab per forzare PyInstaller a includerli
import ui.desktop_app
import ui.bookmaker_tab
import ui.selectors_tab
import ui.robots_tab
import ui.anti_detect_tab
import ui.god_certification_tab
import ui.history_tab
import ui.roserpina_tab
from ui.desktop_app import run_app

# Core imports
from core.controller import SuperAgentController
from core.ai_trainer import AITrainerEngine
from core.health import HealthMonitor
from core.lifecycle import SystemWatchdog
from core.command_parser import CommandParser
from core.logger import setup_logger
from core.event_bus import bus
from core.heartbeat import AppHeartbeat 

def main():
    multiprocessing.freeze_support()
    app = QApplication.instance() or QApplication(sys.argv)

    # Inizializza il logger PRIMA del bootstrap per tracciare eventuali network fault
    logger, log_signaler = setup_logger()
    logger.info("🚀 MAIN: Inizializzazione architettura ULTRA BUILD 11/10 (Hedge-Grade LTM)...")

    # 🛡️ Esegue il check profondo del browser
    ensure_playwright_browsers(logger)

    AppHeartbeat.start()

    try:
        config = {
            "telegram": {},
            "rpa": {"cdp_watchdog": True}
        }

        controller = SuperAgentController(logger)
        executor = controller.worker.executor
        
        trainer = AITrainerEngine(logger=logger)
        trainer.set_executor(executor)
        
        monitor = HealthMonitor(logger)
        watchdog = SystemWatchdog(logger=logger) 
        parser = CommandParser(logger)

        watchdog.start()

        exit_code = run_app(
            logger=logger,
            executor=executor,
            config=config,
            monitor=monitor,
            controller=controller
        )

        logger.info("🔻 Chiusura Main...")
        if hasattr(controller, 'worker'):
            controller.worker.stop()
        
        bus.stop()
        watchdog.stop()
        sys.exit(exit_code)

    except Exception as e:
        if 'logger' in locals():
            logger.critical(f"❌ ERRORE CRITICO MAIN: {e}", exc_info=True)
        else:
            print(f"CRITICAL ERROR: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
