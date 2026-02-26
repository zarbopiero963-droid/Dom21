import sys
import os
import time  # 🔴 IMPORTANTE: Aggiunto per l'Heartbeat OS
from pathlib import Path
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QLabel, QTextEdit, QTabWidget, QLineEdit, QFormLayout, 
                             QPushButton, QMessageBox)
from PySide6.QtCore import Qt, QTimer

from ui.bookmaker_tab import BookmakerTab
from ui.selectors_tab import SelectorsTab
from ui.robots_tab import RobotsTab
from ui.anti_detect_tab import AntiDetectTab
from ui.god_certification_tab import GodCertificationTab
from ui.history_tab import HistoryTab  # 🧠 Nuova importazione Risk Desk
from ui.roserpina_tab import RoserpinaTab  # ⚙️ Nuova importazione Roserpina Config

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
        
        self.session_string_input = QLineEdit()
        self.session_string_input.setEchoMode(QLineEdit.Password)
        if os.path.exists(self.session_file):
            with open(self.session_file, "r", encoding="utf-8") as f: 
                self.session_string_input.setText(f.read().strip())

        self.openrouter_input = QLineEdit()
        self.openrouter_input.setEchoMode(QLineEdit.Password)
        if os.path.exists(self.openrouter_file):
            with open(self.openrouter_file, "r", encoding="utf-8") as f: 
                self.openrouter_input.setText(f.read().strip())

        form_layout.addRow(QLabel("<b>📱 TELEGRAM CLOUD</b>"))
        form_layout.addRow("API ID:", self.api_id_input)
        form_layout.addRow("API Hash:", self.api_hash_input)
        form_layout.addRow("🔑 Session String:", self.session_string_input)
        
        form_layout.addRow(QLabel("<br><b>🧠 AI / OPENROUTER</b>"))
        form_layout.addRow("🔑 API Key:", self.openrouter_input)
        
        layout.addLayout(form_layout)

        save_btn = QPushButton("💾 Salva Chiavi API & Cloud")
        save_btn.setStyleSheet("background-color: #8e44ad; color: white; font-weight: bold; padding: 8px;")
        save_btn.clicked.connect(self._save_settings)
        layout.addWidget(save_btn)
        layout.addStretch()
        self.setLayout(layout)

    def _save_settings(self):
        if "telegram" not in self.config: self.config["telegram"] = {}
        self.config["telegram"]["api_id"] = self.api_id_input.text().strip()
        self.config["telegram"]["api_hash"] = self.api_hash_input.text().strip()
        
        config_loader = __import__('core.config_loader').config_loader.ConfigLoader()
        config_loader.save_config(self.config)
        
        s_str = self.session_string_input.text().strip()
        if s_str: 
            with open(self.session_file, "w", encoding="utf-8") as f: f.write(s_str)
        elif os.path.exists(self.session_file): os.remove(self.session_file)

        or_key = self.openrouter_input.text().strip()
        if or_key: 
            with open(self.openrouter_file, "w", encoding="utf-8") as f: f.write(or_key)
        elif os.path.exists(self.openrouter_file): os.remove(self.openrouter_file)

        QMessageBox.information(self, "Successo", "Chiavi sicure salvate nel Vault Locale.")


class DesktopApp(QMainWindow):
    def __init__(self, logger, executor, config, monitor, controller):
        super().__init__()
        self.logger = logger
        self.controller = controller
        self.config = config
        self.setWindowTitle("SUPERAGENT OS - HEDGE GRADE 24/7")
        self.resize(1300, 850)
        
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QVBoxLayout(main_widget)
        self.tabs = QTabWidget()
        
        # --- TAB DASHBOARD ---
        self.dashboard_tab = QWidget()
        l = QVBoxLayout(self.dashboard_tab)
        l.addWidget(QLabel("<h2>SYSTEM STATUS: 🟢 WATCHDOG OS ACTIVE</h2><p>Tutti i dati sono protetti in ~/.superagent_data/. Backup automatico attivo.</p>"))
        
        # 🔴 MEGA PULSANTE START/STOP
        self.engine_btn = QPushButton("🔴 Avvia Sistema")
        self.engine_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.engine_btn.setStyleSheet("""
            QPushButton { background-color: #d32f2f; color: white; font-size: 24px; font-weight: bold; padding: 25px; border-radius: 10px; }
            QPushButton:hover { background-color: #b71c1c; }
        """)
        self.engine_btn.clicked.connect(self.toggle_engine)
        l.addWidget(self.engine_btn)
        
        l.addStretch()
        
        # --- AGGIUNTA TAB AL WIDGET PRINCIPALE ---
        self.tabs.addTab(self.dashboard_tab, "📊 Dashboard")
        self.tabs.addTab(BookmakerTab(), "💰 Bookmakers")
        self.tabs.addTab(SelectorsTab(), "🧩 Selettori")
        self.tabs.addTab(RobotsTab(self.logger, self.controller), "🤖 Robot & Strategie")
        
        # 🕵️ Aggiunta della Tab Anti-Detect
        self.anti_detect_tab = AntiDetectTab()
        self.tabs.addTab(self.anti_detect_tab, "🕵️ Anti-Detect Lab")

        # 🧠 Aggiunta della Tab God Certification
        self.god_cert_tab = GodCertificationTab()
        self.tabs.addTab(self.god_cert_tab, "🧠 God Certification")

        # 📈 Aggiunta della Tab Risk Desk (Storico & Tavoli)
        self.history_tab = HistoryTab(self.logger, self.controller)
        self.tabs.addTab(self.history_tab, "📈 Risk Desk")
        
        # ⚙️ Aggiunta della Tab Roserpina Config
        self.roserpina_tab = RoserpinaTab(self.logger, self.controller)
        self.tabs.addTab(self.roserpina_tab, "⚙️ Roserpina Config")
        
        self.cloud_tab = CloudApiTab(self.config)
        self.tabs.addTab(self.cloud_tab, "☁️ Cloud & API")
        
        self.logs_tab = QWidget()
        log_l = QVBoxLayout(self.logs_tab)
        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        self.log_output.setStyleSheet("background-color: #1e1e1e; color: #00ff00; font-family: monospace;")
        log_l.addWidget(self.log_output)
        self.tabs.addTab(self.logs_tab, "📝 Logs")
        
        layout.addWidget(self.tabs)
        self.controller.log_message.connect(self.log_output.append)

        # 🔴 Polling di Stato Reale (ogni 1 secondo per reattività)
        self.engine_monitor = QTimer()
        self.engine_monitor.timeout.connect(self.refresh_engine_state)
        self.engine_monitor.start(1000)

    def toggle_engine(self):
        """Richiesta utente: invia il comando ma NON altera la UI. Il Watchdog farà il resto."""
        is_running = getattr(self.controller, 'is_running', False)
        if not is_running:
            self.controller.start_listening()
        else:
            self.controller.stop_listening()
        # RIMOSSO: self.refresh_engine_state() -> Il decoupling esige che lo faccia solo il QTimer

    def refresh_engine_state(self):
        """UI Watchdog: La Source of Truth. Specchia la UI allo stato reale in RAM del backend."""
        try:
            ctrl = self.controller

            # 1. Anti-Freeze Totale (Heartbeat check)
            last_hb = getattr(ctrl, "last_heartbeat", 0)
            if last_hb > 0 and (time.time() - last_hb) > 45:
                self._set_btn_state("💀 ERRORE CRITICO: CONTROLLER DEAD", "#424242", "#212121")
                return

            # 2. Stato Logico Backend
            running = getattr(ctrl, "is_running", False)

            # 3. Stato Worker Playwright
            worker_alive = False
            if hasattr(ctrl, 'worker') and getattr(ctrl.worker, "running", False):
                worker_alive = True

            # 4. Stato Telegram
            telegram_alive = False
            if hasattr(ctrl, 'telegram') and getattr(ctrl.telegram, "running", False):
                telegram_alive = True

            # --- ALBERO DECISIONALE AGGIORNAMENTO VISIVO ---
            if running and worker_alive:
                if telegram_alive:
                    self._set_btn_state("🟢 Sistema Operativo: IN ASCOLTO", "#2e7d32", "#1b5e20")
                else:
                    # Giallo/Arancio: Lavora ma è cieco ai segnali esterni
                    self._set_btn_state("🟠 IN ASCOLTO (ATTENZIONE: Telegram OFF)", "#f57c00", "#e65100")
            elif not running:
                self._set_btn_state("🔴 Avvia Sistema", "#d32f2f", "#b71c1c")
            else:
                # Caso anomalo: controller running ma worker morto
                self._set_btn_state("⚠️ ERRORE: WORKER CRASHATO", "#616161", "#424242")

        except Exception as e:
            self.logger.debug(f"Errore UI Watchdog (Possibile chiusura app in corso): {e}")
            self._set_btn_state("❌ BACKEND SCOLLEGATO", "#424242", "#212121")

    def _set_btn_state(self, text, bg_color, hover_color):
        """Helper per aggiornare il bottone in modo pulito e performante."""
        if self.engine_btn.text() != text:
            self.engine_btn.setText(text)
            self.engine_btn.setStyleSheet(f"""
                QPushButton {{ background-color: {bg_color}; color: white; font-size: 24px; font-weight: bold; padding: 25px; border-radius: 10px; }}
                QPushButton:hover {{ background-color: {hover_color}; }}
            """)

def run_app(logger, executor, config, monitor, controller):
    app = QApplication.instance()
    if not app:
        app = QApplication(sys.argv)
    window = DesktopApp(logger, executor, config, monitor, controller)
    window.show()
    return app.exec()
