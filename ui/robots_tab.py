import logging
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QPushButton, 
                               QLabel, QHBoxLayout, QMessageBox, QGroupBox)
from PySide6.QtCore import Qt, QThread, Signal

class ManualLoginWorker(QThread):
    """
    Thread separato per aprire il browser visibile senza congelare la UI di PySide6.
    """
    finished_signal = Signal(bool)

    def __init__(self, executor, url):
        super().__init__()
        self.executor = executor
        self.url = url

    def run(self):
        try:
            # Chiamata bloccante: aspetta finché l'utente non preme la 'X' su Chrome
            success = self.executor.manual_login_window(self.url)
            self.finished_signal.emit(success)
        except Exception as e:
            logging.getLogger("UI").error(f"Errore fatale in manual_login_window: {e}")
            self.finished_signal.emit(False)


class RobotsTab(QWidget):
    def __init__(self, controller=None):
        super().__init__()
        self.controller = controller
        self.worker = None

        layout = QVBoxLayout(self)

        # =========================================================
        # 🤖 SEZIONE COMANDI ROBOT PRINCIPALI
        # (Se hai già bottoni di Avvio/Stop del bot, vanno qui)
        # =========================================================
        header_label = QLabel("🤖 <b>PANNELLO DI CONTROLLO ROBOT</b>")
        header_label.setStyleSheet("font-size: 16px; margin-bottom: 10px;")
        layout.addWidget(header_label)

        # -- Inserisci qui eventuali altri tuoi bottoni del Robot --
        
        layout.addSpacing(20)

        # =========================================================
        # 🛡️ SEZIONE ANTI-DETECT & ZERO-TOUCH RECOVERY
        # =========================================================
        stealth_group = QGroupBox("🛡️ Gestione Sessione (Anti-Detect & Cloud)")
        stealth_group.setStyleSheet("""
            QGroupBox { 
                font-weight: bold; 
                border: 1px solid #444; 
                border-radius: 8px; 
                margin-top: 15px; 
                padding-top: 20px; 
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
                color: #00ccff;
            }
        """)
        stealth_layout = QVBoxLayout(stealth_group)

        info_label = QLabel(
            "<span style='color: #aaaaaa;'>Se il bot viene bloccato, apri Chrome da qui, fai il login su <b>Bet365</b> e <b>chiudi la finestra</b> per ripristinare i cookie.</span>"
        )
        info_label.setWordWrap(True)
        info_label.setStyleSheet("font-size: 12px; margin-bottom: 10px;")
        stealth_layout.addWidget(info_label)

        # PULSANTE LOGIN MANUALE
        self.login_btn = QPushButton("🔓 APRI BROWSER VISIBILE (LOGIN BET365)")
        self.login_btn.setMinimumHeight(60)
        self.login_btn.setCursor(Qt.PointingHandCursor)
        self.login_btn.setStyleSheet("""
            QPushButton {
                background-color: #b71c1c; 
                color: white; 
                font-weight: bold; 
                font-size: 15px; 
                border: 2px solid #ff5252; 
                border-radius: 8px;
            }
            QPushButton:hover {
                background-color: #d32f2f;
            }
        """)
        self.login_btn.clicked.connect(self.start_manual_login)
        stealth_layout.addWidget(self.login_btn)

        layout.addWidget(stealth_group)
        layout.addStretch()

    # =========================================================
    # LOGICA DI ESECUZIONE
    # =========================================================
    def start_manual_login(self):
        # 1. Controlli di sicurezza
        if not self.controller or not hasattr(self.controller, 'worker') or not self.controller.worker:
            QMessageBox.warning(self, "Attenzione", "Il motore non è ancora completamente avviato.")
            return
            
        executor = self.controller.worker.executor
        if not executor:
            QMessageBox.warning(self, "Attenzione", "L'esecutore Browser non è disponibile.")
            return

        # 2. Modifica grafica del bottone (Stato di attesa)
        self.login_btn.setEnabled(False)
        self.login_btn.setText("⏳ BROWSER APERTO A SCHERMO... (Fai login e chiudi la finestra con la 'X')")
        self.login_btn.setStyleSheet("""
            QPushButton {
                background-color: #e65100; 
                color: white; 
                font-weight: bold; 
                font-size: 14px; 
                border: 2px solid #ffb300; 
                border-radius: 8px;
            }
        """)

        # 3. Lancio del worker asincrono col link di Bet365
        bet365_url = "https://www.bet365.it/#/HO/"
        self.worker = ManualLoginWorker(executor, bet365_url)
        self.worker.finished_signal.connect(self.on_login_finished)
        self.worker.start()

    def on_login_finished(self, success):
        # 4. Ripristino bottone quando chiudi Chrome
        self.login_btn.setEnabled(True)
        self.login_btn.setText("🔓 APRI BROWSER VISIBILE (LOGIN BET365)")
        self.login_btn.setStyleSheet("""
            QPushButton {
                background-color: #b71c1c; 
                color: white; 
                font-weight: bold; 
                font-size: 15px; 
                border: 2px solid #ff5252; 
                border-radius: 8px;
            }
            QPushButton:hover {
                background-color: #d32f2f;
            }
        """)
        
        if success:
            QMessageBox.information(self, "Sessione Ripristinata", "✅ Cookie salvati con successo!\nIl bot riprenderà le scommesse in modalità fantasma (invisibile).")
        else:
            QMessageBox.critical(self, "Errore", "❌ Operazione annullata o fallita. Il browser è stato chiuso forzatamente.")
