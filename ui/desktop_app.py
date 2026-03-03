import sys
import os
import logging
import time
from pathlib import Path
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QLabel, QTextEdit, QTabWidget, QLineEdit, QFormLayout, 
                             QPushButton, QMessageBox)
from PySide6.QtCore import Qt, QTimer, QMetaObject, Q_ARG

from ui.bookmaker_tab import BookmakerTab
from ui.selectors_tab import SelectorsTab
from ui.robots_tab import RobotsTab
from ui.anti_detect_tab import AntiDetectTab
from ui.god_certification_tab import GodCertificationTab
from ui.history_tab import HistoryTab
from ui.roserpina_tab import RoserpinaTab
from core.logger import setup_global_logger

class CloudApiTab(QWidget):
    def __init__(self, config):
        super().__init__()
        self.config = config
        self.save_dir = os.path.join(str(Path.home()), ".superagent_data")
        os.makedirs(self.save_dir, exist_ok=True)
        
        self.session_file = os.path.join(self.save_dir, "telegram_session.dat")
        self.openrouter_file = os.path.join(self.save_dir, "openrouter_key.dat")

        layout = QVBoxLayout()
        form_layout = QFormLayout()
        
        self.api_id_input = QLineEdit(str(config.get("telegram", {}).get("api_id", "")))
        self.api_hash_input = QLineEdit(config.get("telegram", {}).get("api_hash", ""))
        self.api_hash_input.setEchoMode(QLineEdit.Password)
        
        self.session_string_input = QLineEdit()
        self.session_string_input.setEchoMode(QLineEdit.Password)
        if os.path.exists(self.session_file):
            self.session_string_input.setText("********************************")

        self.openrouter_input = QLineEdit()
        self.openrouter_input.setEchoMode(QLineEdit.Password)
        if os.path.exists(self.openrouter_file):
            self.openrouter_input.setText("********************************")

        form_layout.addRow("Telegram API ID:", self.api_id_input)
        form_layout.addRow("Telegram API Hash:", self.api_hash_input)
        form_layout.addRow("Telegram Session String:", self.session_string_input)
        form_layout.addRow("OpenRouter API Key (Llama-3):", self.openrouter_input)

        save_btn = QPushButton("💾 Salva Chiavi API & Cloud")
        save_btn.setStyleSheet("background-color: #2b2b2b; color: #00ff00; padding: 10px; font-weight: bold;")
        save_btn.clicked.connect(self.save_keys)

        layout.addLayout(form_layout)
        layout.addWidget(save_btn)
        self.setLayout(layout)

    def save_keys(self):
        logging.info("🖱️ [UI] Cliccato salvataggio Chiavi API.")
        session_val = self.session_string_input.text()
        if session_val and "*" not in session_val:
            with open(self.session_file, "w") as f:
                f.write(session_val)
            self.session_string_input.setText("********************************")
            logging.info("🔑 [VAULT] Telegram Session String salvata e criptata.")

        or_val = self.openrouter_input.text()
        if or_val and "*" not in or_val:
            with open(self.openrouter_file, "w") as f:
                f.write(or_val)
            self.openrouter_input.setText("********************************")
            logging.info("🔑 [VAULT] OpenRouter API Key salvata e criptata.")

        QMessageBox.information(self, "API Cloud", "✅ Chiavi salvate nel Vault locale in modo sicuro.")

class Dom21App(QMainWindow):
    def __init__(self, controller):
        super().__init__()
        self.controller = controller
        self.setWindowTitle("SuperAgent OS - Algorithmic Trading Desk")
        self.resize(1200, 800)
        self.setStyleSheet("background-color: #121212; color: #e0e0e0; font-family: 'Segoe UI', Arial, sans-serif;")

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        # Tab Widget Principale
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet("""
            QTabBar::tab { background: #2d2d2d; color: white; padding: 10px 20px; border-top-left-radius: 4px; border-top-right-radius: 4px; margin-right: 2px;}
            QTabBar::tab:selected { background: #1e88e5; font-weight: bold; }
            QTabWidget::pane { border: 1px solid #333; background: #1a1a1a; }
        """)

        # Creazione del widget Logs in anticipo per poterlo passare al logger
        self.logs_text_edit = QTextEdit()
        self.logs_text_edit.setReadOnly(True)
        self.logs_text_edit.setStyleSheet("background-color: #000000; color: #00ff00; font-family: 'Consolas', monospace; font-size: 12px; padding: 10px;")

        # INIZIALIZZAZIONE LOGGER GLOBALE
        # Inietta la callback della UI nel sistema di logging del bot
        self.logger = setup_global_logger(ui_callback=self.append_log_to_ui)
        self.logger.info("🚀 SUPERAGENT OS AVVIATO E PRONTO.")

        # Tab 1: Dashboard
        dash_tab = QWidget()
        dash_layout = QVBoxLayout()
        title = QLabel("🖥️ SUPERAGENT OS - HEDGE FUND EDITION (V8.5)")
        title.setStyleSheet("font-size: 24px; font-weight: bold; color: white; margin-bottom: 20px;")
        title.setAlignment(Qt.AlignCenter)
        dash_layout.addWidget(title)
        
        info = QLabel("Sistema operativo connesso e protetto. Vault cifrato attivo. Pronto per operare 24/7.")
        info.setAlignment(Qt.AlignCenter)
        dash_layout.addWidget(info)
        dash_layout.addStretch()

        # Pulsante Engine Start/Stop Globale
        self.engine_btn = QPushButton("🔴 Avvia Sistema")
        self.engine_btn.setCursor(Qt.PointingHandCursor)
        self._set_btn_state("🔴 Avvia Sistema", "#d32f2f", "#b71c1c")
        self.engine_btn.clicked.connect(self.toggle_engine)
        dash_layout.addWidget(self.engine_btn)
        dash_tab.setLayout(dash_layout)

        # Aggiunta Tabs
        self.tabs.addTab(dash_tab, "📊 Dashboard")
        self.tabs.addTab(BookmakerTab(), "💰 Bookmakers")
        self.tabs.addTab(SelectorsTab(), "🧩 Selettori")
        self.tabs.addTab(RobotsTab(self.controller), "🤖 Robot & Strategie")
        self.tabs.addTab(AntiDetectTab(), "🕵️ Anti-Detect Lab")
        self.tabs.addTab(GodCertificationTab(), "🧠 God Certification")
        
        # Risk Desk (Tab Storico avanzata)
        self.history_tab = HistoryTab(self.logger, self.controller)
        self.tabs.addTab(self.history_tab, "📈 Risk Desk")
        
        # Roserpina Config (Configurazione Risk Engine)
        self.roserpina_tab = RoserpinaTab(self.logger, self.controller)
        self.tabs.addTab(self.roserpina_tab, "⚙️ Roserpina Config")

        self.tabs.addTab(CloudApiTab(self.controller.config), "☁️ Cloud & API")
        
        # Tab Logs
        logs_tab = QWidget()
        logs_layout = QVBoxLayout(logs_tab)
        logs_layout.addWidget(QLabel("📝 SYSTEM LOGS (Live):"))
        logs_layout.addWidget(self.logs_text_edit)
        self.tabs.addTab(logs_tab, "📝 Logs")

        main_layout.addWidget(self.tabs)

        # Watchdog per UI
        self.watchdog_timer = QTimer(self)
        self.watchdog_timer.timeout.connect(self.update_ui_state)
        self.watchdog_timer.start(2000)

    def append_log_to_ui(self, message):
        """Riceve messaggi dal logger e li aggiunge in modo sicuro nella text edit."""
        # Usa invokeMethod per garantire la sicurezza del thread nella GUI
        QMetaObject.invokeMethod(self.logs_text_edit, "appendPlainText", Qt.QueuedConnection, Q_ARG(str, message))

    def toggle_engine(self):
        logging.info("🖱️ [UI] Utente ha premuto il tasto START/STOP Motore Principale.")
        if not self.controller.is_running:
            self.logger.info("⚙️ Avvio del motore Controller richiesto...")
            self.controller.start()
            self._set_btn_state("🟢 Sistema Operativo: IN ASCOLTO", "#2e7d32", "#1b5e20")
        else:
            self.logger.warning("🛑 SSpegnimentopegnimento del motore Controller in corso...")
            self.controller.stop()
            self._set_btn_state("🔴 Avvia Sistema", "#d32f2f", "#b71c1c")

    def update_ui_state(self):
        """Aggiorna lo stato dei bottoni in base allo stato reale del Controller."""
        try:
            running = getattr(self.controller, 'is_running', False)
            worker_alive = self.controller.playwright_worker.is_alive() if hasattr(self.controller, 'playwright_worker') else False
            telegram_alive = self.controller.telegram.is_running if hasattr(self.controller, 'telegram') else False

            if running and worker_alive:
                if telegram_alive:
                    self._set_btn_state("🟢 Sistema Operativo: IN ASCOLTO", "#2e7d32", "#1b5e20")
                else:
                    self._set_btn_state("🟠 IN ASCOLTO (Telegram OFF)", "#f57c00", "#e65100")
            elif not running:
                self._set_btn_state("🔴 Avvia Sistema", "#d32f2f", "#b71c1c")
            else:
                self._set_btn_state("⚠️ ERRORE: WORKER CRASHATO", "#616161", "#424242")
                logging.error("❌ [UI WATCHDOG] Rilevato crash del Playwright Worker.")

        except Exception as e:
            self.logger.debug(f"Errore UI Watchdog: {e}")
            self._set_btn_state("❌ BACKEND SCOLLEGATO", "#424242", "#212121")

    def _set_btn_state(self, text, bg_color, hover_color):
        if self.engine_btn.text() != text:
            self.engine_btn.setText(text)
            self.engine_btn.setStyleSheet(f"""
                QPushButton {{ background-color: {bg_color}; color: white; font-size: 24px; font-weight: bold; padding: 25px; border-radius: 10px; }}
                QPushButton:hover {{ background-color: {hover_color}; }}
            """)

# ==============================================================================
# 🔥 FUNZIONE MANCANTE RIPRISTINATA: Avvia l'interfaccia da main.py
# ==============================================================================
def run_app(controller):
    app = QApplication(sys.argv)
    window = Dom21App(controller)
    window.show()
    return app.exec()
