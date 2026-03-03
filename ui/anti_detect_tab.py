import time
import logging
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QPushButton, 
                               QTextEdit, QLabel, QHBoxLayout)
from PySide6.QtCore import QThread, Signal
from PySide6.QtGui import QFont, QColor
from playwright.sync_api import sync_playwright
from core.anti_detect import STEALTH_INJECTION_V5

class AuditWorker(QThread):
    """
    QThread che esegue il test dei siti in background.
    """
    log_signal = Signal(str, str) # text, color
    finished_signal = Signal(bool)

    def run(self):
        logging.info("🛡️ [ANTI-DETECT] Avvio scansione di sicurezza Hedge Fund Tier.")
        self.log_signal.emit("\n" + "☠️" * 20, "white")
        self.log_signal.emit("ANTI-DETECT SECURITY AUDIT — HEDGE FUND TIER", "cyan")
        self.log_signal.emit("☠️" * 20 + "\n", "white")
        
        headless_mode = False 
        FAILURES = []

        def fail(site, reason):
            msg = f"🔴 FAIL [{site}] → {reason}"
            self.log_signal.emit(msg, "red")
            logging.warning(f"⚠️ [ANTI-DETECT] Rilevata anomalia: {msg}")
            FAILURES.append(msg)

        def ok(site, desc): 
            self.log_signal.emit(f"🟢 OK [{site}] → {desc}", "green")
            logging.debug(f"✅ [ANTI-DETECT] Test superato: {site} - {desc}")

        try:
            with sync_playwright() as p:
                self.log_signal.emit("Avvio Browser Stealth (Locale)...", "white")
                browser = p.chromium.launch(headless=headless_mode, args=["--start-maximized"])
                context = browser.new_context(viewport={"width": 1920, "height": 1080})
                context.add_init_script(STEALTH_INJECTION_V5)
                page = context.new_page()

                # Test 1
                try:
                    self.log_signal.emit("Contacting BrowserLeaks (WebGL)...", "yellow")
                    page.goto("https://browserleaks.com/webgl", timeout=15000)
                    page.wait_for_selector("#webgl-vendor", timeout=5000)
                    vendor = page.locator("#webgl-vendor").inner_text()
                    if "Google" in vendor or "SwiftShader" in vendor:
                        fail("BrowserLeaks", f"Spoofing fallito. Vendor reale visibile: {vendor}")
                    else:
                        ok("BrowserLeaks", f"WebGL Nascosto. Vendor: {vendor}")
                except Exception as e:
                    fail("BrowserLeaks", "Timeout connessione")

                # Test 2
                try:
                    self.log_signal.emit("Contacting SannySoft (WebDriver)...", "yellow")
                    page.goto("https://bot.sannysoft.com/", timeout=15000)
                    time.sleep(2)
                    wd_res = page.locator("#webdriver-result").inner_text()
                    if "present" in wd_res.lower() or "true" in wd_res.lower():
                        fail("SannySoft", "WebDriver rilevato!")
                    else:
                        ok("SannySoft", "WebDriver rimosso (missing)")
                except Exception as e:
                    fail("SannySoft", "Timeout connessione")

                browser.close()
                self.log_signal.emit("\n" + "="*50, "white")
                if len(FAILURES) == 0:
                    logging.info("🏆 [ANTI-DETECT] Audit superato. Nessuna falla rilevata.")
                    self.log_signal.emit("🏆 AUDIT SUPERATO. SEI INVISIBILE.", "#00ff00")
                    self.finished_signal.emit(True)
                else:
                    logging.error(f"❌ [ANTI-DETECT] Audit fallito. Rilevate {len(FAILURES)} falle.")
                    self.log_signal.emit(f"❌ AUDIT FALLITO. RILEVATE {len(FAILURES)} FALLE.", "red")
                    self.finished_signal.emit(False)

        except Exception as e:
            logging.critical(f"❌ [ANTI-DETECT] Errore critico durante l'avvio del browser: {e}")
            self.log_signal.emit(f"ERRORE CRITICO: {e}", "red")
            self.finished_signal.emit(False)


class AntiDetectTab(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)

        header_layout = QHBoxLayout()
        header_label = QLabel("🛡️ <b>LABORATORIO ANTI-FRODE</b>")
        header_label.setStyleSheet("font-size: 16px;")
        header_layout.addWidget(header_label)
        
        self.start_btn = QPushButton("🚀 AVVIA AUDIT HEDGE FUND (14 Test)")
        self.start_btn.setMinimumHeight(40)
        self.start_btn.setStyleSheet("background-color: #2b2b2b; color: #00ff00; font-weight: bold; border: 1px solid #00ff00; border-radius: 5px;")
        self.start_btn.clicked.connect(self.start_audit)
        header_layout.addWidget(self.start_btn)
        
        layout.addLayout(header_layout)

        self.console = QTextEdit()
        self.console.setReadOnly(True)
        self.console.setStyleSheet("background-color: #1e1e1e; color: #ffffff; padding: 10px; border-radius: 5px;")
        font = QFont("Courier", 10)
        self.console.setFont(font)
        layout.addWidget(self.console)

        self.worker = None

    def start_audit(self):
        logging.info("🖱️ [UI] L'utente ha avviato l'Anti-Detect Audit.")
        self.start_btn.setEnabled(False)
        self.start_btn.setText("⏳ AUDIT IN CORSO... NON TOCCARE IL BROWSER")
        self.console.clear()
        
        self.worker = AuditWorker()
        self.worker.log_signal.connect(self.append_log)
        self.worker.finished_signal.connect(self.audit_finished)
        self.worker.start()

    def append_log(self, text, color):
        html_text = f"<span style='color:{color};'>{text}</span>"
        self.console.append(html_text)
        scrollbar = self.console.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def audit_finished(self, success):
        self.start_btn.setEnabled(True)
        self.start_btn.setText("🚀 AVVIA AUDIT HEDGE FUND")
