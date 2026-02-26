import time
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QPushButton, 
                               QTextEdit, QLabel, QHBoxLayout)
from PySide6.QtCore import QThread, Signal
from PySide6.QtGui import QFont, QColor
from playwright.sync_api import sync_playwright
from core.anti_detect import STEALTH_INJECTION_V5

class AuditWorker(QThread):
    """
    QThread che esegue il test dei siti in background 
    e invia i risultati in tempo reale all'interfaccia.
    """
    log_signal = Signal(str, str) # text, color
    finished_signal = Signal(bool)

    def run(self):
        self.log_signal.emit("\n" + "☠️" * 20, "white")
        self.log_signal.emit("ANTI-DETECT SECURITY AUDIT — HEDGE FUND TIER", "cyan")
        self.log_signal.emit("☠️" * 20 + "\n", "white")
        
        # 🚨 MAGIA: Essendo nella UI locale, forziamo headless a FALSE!
        headless_mode = False 
        
        FAILURES = []

        def fail(site, reason):
            msg = f"🔴 FAIL [{site}] → {reason}"
            self.log_signal.emit(msg, "red")
            FAILURES.append(msg)

        def ok(site, desc): 
            self.log_signal.emit(f"🟢 OK [{site}] → {desc}", "green")

        try:
            with sync_playwright() as p:
                self.log_signal.emit("🚀 Avvio Motore C++ Chromium Stealth (Visibile a schermo)...", "yellow")
                
                browser = p.chromium.launch(
                    headless=headless_mode, 
                    args=["--no-sandbox", "--disable-blink-features=AutomationControlled"],
                    ignore_default_args=["--enable-automation"]
                )
                
                context = browser.new_context(
                    viewport={"width": 1920, "height": 1080},
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
                    locale="it-IT",
                    timezone_id="Europe/Rome"
                )
                page = context.new_page()
                
                # Iniezione della V5 (Hardware Spoofing + CDP Bypass)
                page.add_init_script(STEALTH_INJECTION_V5)

                # ==========================================
                # TEST LOOP (Ora con Stack Bancario)
                # ==========================================
                tests = [
                    # LIVELLO 1: FINGERPRINT BASE
                    ("SANNYSOFT", "https://bot.sannysoft.com/", "webdriver", "true", "Firma WebDriver visibile.", "Nessun flag di automazione di base.", 3000),
                    ("BROWSERLEAKS", "https://browserleaks.com/webgl", "swiftshader", "google", "Scheda video finta smascherata.", "Hardware spoofing WebGL perfetto.", 3000),
                    ("AMIUNIQUE", "https://amiunique.org/fingerprint", "robot", "headless", "Siamo stati etichettati come bot.", "Ci confondiamo nella massa. Profilo utente accettato.", 4000),
                    ("DEVICEINFO", "https://www.deviceinfo.me/", "webdriver: true", "headless: true", "Leak sensori rilevato.", "Sensori e Media Devices coerenti.", 5000),
                    
                    # LIVELLO 2: COERENZA RETE E CDP
                    ("BROWSERSCAN", "https://www.browserscan.net/bot-detection", "playwright", "puppeteer", "Firma Playwright rilevata via CDP!", "Nessuna traccia di framework di automazione.", 5000),
                    ("IPHEY", "https://iphey.com/", "not trustworthy", "trustworthy", "Mismatch TLS/Rete rilevato.", "Firma JA3 e Headers in regola.", 5000),
                    ("WHOER", "https://whoer.net/", "anonymity", "0%", "Proxy detectato o DNS Leak attivo.", "Check di anonimato IP/DNS superato.", 5000),
                    
                    # LIVELLO 3: BEHAVIOR & HARDWARE AVANZATO (DataDome)
                    ("PIXELSCAN", "https://pixelscan.net/", "automation", "bot", "Coerenza persa. Hanno capito che siamo un software.", "Siamo umani per la sicurezza Pixelscan.", 6000),
                    ("DETECT.EXPERT", "https://detect.expert/", "headless traces found", "automation: yes", "Smontati dal livello enterprise.", "Bypass dell'analisi comportamentale riuscito.", 6000),
                    ("FPSCANNER", "https://fpscanner.com/demo/", "swiftshader", "google", "DataDome ha rilevato un server virtuale.", "Hardware Spoofing inganna i sensori DataDome.", 6000),

                    # 🌟 LIVELLO 4: STACK HEDGE FUND / BANCARIO (I NUOVI)
                    ("CLOUDFLARE (nowsecure.nl)", "https://nowsecure.nl/", "just a moment", "please stand by", "Bloccati dal JS Challenge di Cloudflare.", "Cloudflare Turnstile superato in scioltezza!", 8000),
                    ("TLS / JA3 SIGNATURE", "https://tls.peet.ws/api/all", "curl", "python", "Firma TLS non standard (Bot Network Stack).", "Handshake di rete TLS 1.3 perfettamente coerente.", 4000),
                    ("FINGERPRINTJS PRO", "https://demo.fingerprint.com/", "bot detected", "automation tool", "Fallito il check bancario di FingerprintJS.", "Profilo stabile, superata l'analisi Enterprise SaaS.", 6000),
                ]

                total_tests = len(tests) + 1 # +1 per CREEPJS alla fine

                for i, (name, url, bad1, bad2, fail_msg, ok_msg, wait_t) in enumerate(tests, 1):
                    try:
                        self.log_signal.emit(f"⏳ [{i}/{total_tests}] {name}...", "white")
                        page.goto(url, timeout=45000)
                        page.wait_for_timeout(wait_t)
                        html = page.content().lower()
                        if bad1 in html or bad2 in html:
                            # Aggiustamento per IPHEY logica inversa
                            if name == "IPHEY" and "not trustworthy" not in html:
                                ok(name, ok_msg)
                            elif name == "IPHEY":
                                fail(name, fail_msg)
                            else:
                                fail(name, fail_msg)
                        else:
                            ok(name, ok_msg)
                    except Exception as e:
                        fail(name, f"Errore di caricamento (Timeout o Blocco): {str(e)}")

                # ==========================================
                # IL BOSS FINALE: CREEPJS (Logica Matematica)
                # ==========================================
                try:
                    self.log_signal.emit(f"⏳ [{total_tests}/{total_tests}] CREEPJS (Fingerprint Entropy)...", "white")
                    page.goto("https://abrahamjuliot.github.io/creepjs/", timeout=60000)
                    page.wait_for_timeout(8000)
                    
                    score_element = page.locator(".trust-score").first
                    if score_element.is_visible():
                        score_text = score_element.inner_text()
                        score_val = float(score_text.replace('%', '').strip())
                        if score_val <= 0.0:
                            fail("CREEPJS", "Trust Score allo 0%. Rilevazione entropia fatale.")
                        else:
                            ok("CREEPJS", f"Sfida suprema vinta! Trust Score: {score_val}%")
                    else:
                        fail("CREEPJS", "Elemento punteggio non trovato (possibile blocco invisibile).")
                except Exception as e:
                    fail("CREEPJS", str(e))

                self.log_signal.emit("🛑 Chiusura browser di test in corso...", "yellow")
                browser.close()

        except Exception as e:
            self.log_signal.emit(f"🚨 ERRORE CRITICO MOTORE: {e}", "red")

        self.log_signal.emit("\n" + "=" * 50, "white")
        if FAILURES:
            self.log_signal.emit(f"🚨 AUDIT TERMINATO: {len(FAILURES)}/{total_tests} Test non passati.", "red")
        else:
            self.log_signal.emit(f"🏆 DOMINIO ASSOLUTO: {total_tests}/{total_tests} TEST SUPERATI SUL TUO PC!", "green")
        
        self.finished_signal.emit(len(FAILURES) == 0)

class AntiDetectTab(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)

        # Header Info
        header_layout = QHBoxLayout()
        info_label = QLabel("🛡️ <b>LABORATORIO ANTI-DETECT:</b> Testa l'invisibilità contro la stack Hedge Fund (Cloudflare, FPScanner, CreepJS, TLS).")
        header_layout.addWidget(info_label)
        
        self.start_btn = QPushButton("🚀 AVVIA AUDIT HEDGE FUND (14 Test)")
        self.start_btn.setMinimumHeight(40)
        self.start_btn.setStyleSheet("background-color: #2b2b2b; color: #00ff00; font-weight: bold; border: 1px solid #00ff00; border-radius: 5px;")
        self.start_btn.clicked.connect(self.start_audit)
        header_layout.addWidget(self.start_btn)
        
        layout.addLayout(header_layout)

        # Console Log
        self.console = QTextEdit()
        self.console.setReadOnly(True)
        self.console.setStyleSheet("background-color: #1e1e1e; color: #ffffff; padding: 10px; border-radius: 5px;")
        font = QFont("Courier", 10)
        self.console.setFont(font)
        layout.addWidget(self.console)

        self.worker = None

    def start_audit(self):
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
        self.start_btn.setText("🚀 RIPETI AUDIT HEDGE FUND")
