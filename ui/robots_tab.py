import logging
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QPushButton, 
                               QLabel, QHBoxLayout, QMessageBox, QGroupBox)
from PySide6.QtCore import Qt, QThread, Signal

class ManualLoginWorker(QThread):
    """
    Thread separato per aprire il browser visibile senza congelare la UI.
    """
    finished_signal = Signal(bool)

    def __init__(self, executor, url):
        super().__init__()
        self.executor = executor
        self.url = url

    def run(self):
        try:
            # Chiamata bloccante al motore Playwright
            success = self.executor.manual_login_window(self.url)
            self.finished_signal.emit(success)
        except Exception as e:
            logging.error(f"❌ [ROBOTS] Errore fatale in manual_login_window: {e}")
            self.finished_signal.emit(False)


class RobotsTab(QWidget):
    def __init__(self, controller=None):
        super().__init__()
        self.controller = controller
        self.worker = None

        layout = QVBoxLayout(self)

        # --- SEZIONE 1: COMANDI PRINCIPALI ---
        header_label = QLabel("🤖 <b>PANNELLO DI CONTROLLO ROBOT</b>")
        header_label.setStyleSheet("font-size: 18px; margin-bottom: 10px; color: #00ccff;")
        layout.addWidget(header_label)

        # --- SEZIONE 2: LOGIN MANUALE ---
        login_group = QGroupBox("Accesso Diretto Bookmaker")
        login_layout = QVBoxLayout()
        
        self.login_btn = QPushButton("🔓 APRI BROWSER VISIBILE (LOGIN BET365)")
        self.login_btn.setMinimumHeight(60)
        self.login_btn.setStyleSheet("""
            QPushButton {
                background-color: #b71c1c; 
                color: white; 
                font-weight: bold; 
                font-size: 15px; 
                border: 2px solid #ff5252; 
                border-radius: 8px;
            }
            QPushButton:hover { background-color: #d32f2f; }
        """)
        self.login_btn.clicked.connect(self.start_login)
        login_layout.addWidget(self.login_btn)
        
        desc = QLabel("Usa questo tasto se il bot viene bloccato da un Captcha o se devi effettuare il login iniziale.")
        desc.setWordWrap(True)
        desc.setStyleSheet("color: #aaaaaa; font-style: italic;")
        login_layout.addWidget(desc)
        
        login_group.setLayout(login_layout)
        layout.addWidget(login_group)
        
        layout.addStretch()

    def start_login(self):
        logging.info("🖱️ [UI] Richiesta apertura browser visibile per Login Manuale.")
        
        if not self.controller or not hasattr(self.controller, 'executor'):
            logging.error("❌ [UI] Impossibile avviare login: Motore non inizializzato.")
            QMessageBox.critical(self, "Errore", "Il motore Playwright non è attivo.")
            return

        executor = self.controller.executor
        self.login_btn.setEnabled(False)
        self.login_btn.setText("⏳ CHROME ATTIVO... LOGGATI E POI CHIUDI LA FINESTRA")
        self.login_btn.setStyleSheet("background-color: #e65100; color: white; border-radius: 8px;")

        # Avvio del worker per non bloccare l'interfaccia
        bet365_url = "https://www.bet365.it/#/HO/"
        self.worker = ManualLoginWorker(executor, bet365_url)
        self.worker.finished_signal.connect(self.on_login_finished)
        self.worker.start()

    def on_login_finished(self, success):
        # Ripristino interfaccia
        self.login_btn.setEnabled(True)
        self.login_btn.setText("🔓 APRI BROWSER VISIBILE (LOGIN BET365)")
        self.login_btn.setStyleSheet("""
            QPushButton {
                background-color: #b71c1c; 
                color: white; 
                font-weight: bold; 
                font-size: 15px; 
                border-radius: 8px;
            }
        """)
        
        if success:
            logging.info("✅ [ROBOTS] Sessione ripristinata con successo. Cookie salvati.")
            QMessageBox.information(self, "Sessione Ripristinata", "✅ Cookie salvati con successo!\nIl bot riprenderà l'operatività stealth.")
        else:
            logging.warning("⚠️ [ROBOTS] Login manuale chiuso o fallito.")
