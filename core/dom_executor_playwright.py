import threading
import logging
import os
import time
import re
from playwright.sync_api import sync_playwright

class DomExecutorPlaywright:
    def __init__(self, logger=None, allow_place=False):
        self.logger = logger or logging.getLogger("DomExecutor")
        self.allow_place = allow_place
        self.playwright = self.context = self.page = None
        self._browser_lock = threading.Lock()
        self.is_visible_mode = False
        self._chaos_hooks = {}  # Fondamentale per il GOD_MODE_V2_chaos.py

    def launch_browser(self, headless=True):
        """Avvia Chrome con profilo reale e protezioni Stealth."""
        with self._browser_lock:
            if self.context and self.page and not self.page.is_closed():
                if self.is_visible_mode == (not headless):
                    return True
                else:
                    self._stop_unlocked()

            try:
                self.playwright = sync_playwright().start()
                self.is_visible_mode = not headless
                
                stealth_args = [
                    '--disable-blink-features=AutomationControlled',
                    '--start-maximized',
                    '--no-sandbox',
                    '--disable-dev-shm-usage',
                    '--ignore-certificate-errors',
                    '--disable-web-security'
                ]
                
                user_data_path = os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\User Data")
                
                real_chrome_path = None
                possible_paths = [
                    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
                    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
                    os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe")
                ]
                
                for path in possible_paths:
                    if os.path.exists(path):
                        real_chrome_path = path
                        break

                launch_options = {
                    "user_data_dir": user_data_path,
                    "headless": headless,
                    "args": stealth_args,
                    "no_viewport": True,
                    "ignore_default_args": ["--enable-automation"],
                    "bypass_csp": True,
                    "java_script_enabled": True,
                }

                if real_chrome_path:
                    launch_options["executable_path"] = real_chrome_path

                self.logger.info(f"🚀 Avvio Chrome Reale (Headless={headless})...")
                self.context = self.playwright.chromium.launch_persistent_context(**launch_options)
                
                # Script Stealth anti-rivelazione
                stealth_js = """
                    Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
                    window.chrome = { runtime: {} };
                """
                self.context.add_init_script(stealth_js)
                
                if len(self.context.pages) > 0:
                    self.page = self.context.pages[0]
                else:
                    self.page = self.context.new_page()
                    
                return True
            except Exception as e:
                self.logger.error(f"🚨 ERRORE AVVIO BROWSER: {e}")
                self._stop_unlocked()
                return False

    def _stop_unlocked(self):
        try:
            if self.context: self.context.close()
            if self.playwright: self.playwright.stop()
        except: pass
        finally: self.context = self.playwright = self.page = None

    def stop(self):
        """Spegne il motore del browser."""
        with self._browser_lock:
            self._stop_unlocked()

    def close(self):
        """Metodo richiesto dai Test di Integrità (Alias di stop)."""
        self.stop()

    def recycle_browser(self):
        """Metodo richiesto dal tester: riavvia la sessione pulita."""
        self.logger.info("🔄 Riciclo del browser in corso...")
        self.stop()
        time.sleep(1)
        return self.launch_browser(headless=not self.is_visible_mode)

    def manual_login_window(self, url="https://www.bet365.it/#/HO/"):
        self.logger.warning("🖥️ Apertura finestra per login manuale...")
        self.stop()
        time.sleep(1)
        success = self.launch_browser(headless=False)
        if success and self.page:
            try:
                self.page.goto(url)
                self.page.wait_for_event("close", timeout=0) 
            except: pass
            self.stop()
            self.launch_browser(headless=True)
            return True
        return False

    def check_health(self):
        with self._browser_lock:
            if not self.page or self.page.is_closed(): return False
            try: 
                self.page.evaluate("1")
                return True
            except: return False

    def get_balance(self):
        """Legge il saldo reale dal DOM."""
        with self._browser_lock:
            if not self.page or self.page.is_closed(): return 0.0
        try:
            selectors = [".hm-Balance", ".nav-top__balance", "[data-c='HeaderBalance']"]
            for s in selectors:
                if self.page.locator(s).count() > 0:
                    txt = self.page.locator(s).first.inner_text()
                    clean = re.sub(r'[^\d,.]', '', txt).replace('.', '').replace(',', '.')
                    return float(clean)
            return 0.0
        except: return 0.0

    def place_bet(self, teams, market, stake, test_mode=False):
        """Protocollo di scommessa reale End-to-End."""
        if "place_bet" in self._chaos_hooks: 
            return self._chaos_hooks["place_bet"](teams, market, stake)
            
        with self._browser_lock:
            if not self.page or self.page.is_closed(): 
                self.logger.error("❌ Errore: Browser chiuso o disconnesso.")
                return False

        try:
            self.logger.info(f"🎯 Protocollo Scommessa INIZIATO: {teams} @ {market} | Stake: €{stake}")
            time.sleep(1.5)
            
            # --- 1. RICERCA PARTITA ---
            search_icon_selector = ".hm-HeaderSearchIcon"
            if self.page.locator(search_icon_selector).count() > 0:
                self.page.locator(search_icon_selector).first.click(delay=150)
                time.sleep(1)
                
                search_input_selector = ".sml-SearchTextInput"
                if self.page.locator(search_input_selector).count() > 0:
                    self.logger.info(f"⌨️ Digitazione squadra: {teams[:15]}")
                    self.page.locator(search_input_selector).first.type(teams[:15], delay=120) 
                    time.sleep(2) 
                else:
                    self.logger.error("❌ Impossibile trovare la barra di ricerca testo.")
                    return False
            else:
                self.logger.error("❌ Impossibile trovare l'icona di ricerca.")
                return False

            # --- 2. APERTURA EVENTO ---
            try:
                 self.page.keyboard.press("Enter")
                 time.sleep(3)
            except: 
                 self.logger.error("❌ Fallito caricamento pagina evento.")
                 return False

            # --- 3. SELEZIONE QUOTA/MERCATO ---
            self.logger.info(f"🖱️ Ricerca della quota a schermo: '{market}'...")
            self.page.mouse.wheel(0, 400) # Scrolla giù per caricare i mercati
            time.sleep(1.5)

            try:
                # Cerca l'elemento che contiene il testo esatto del mercato/quota
                market_locator = self.page.get_by_text(market, exact=True).first
                if market_locator.count() > 0:
                    market_locator.click(delay=150)
                    self.logger.info("✅ Quota cliccata con successo.")
                    time.sleep(1.5)
                else:
                    self.logger.error(f"❌ Impossibile trovare la quota o il mercato '{market}' a schermo.")
                    return False
            except Exception as e:
                self.logger.error(f"❌ Errore durante il click sulla quota: {e}")
                return False

            # --- 4. COMPILAZIONE SCHEDINA ---
            self.logger.info("🧾 Apertura Schedina in corso...")
            betslip_input_selector = ".bs-Stake_Input"
            if self.page.locator(betslip_input_selector).count() > 0:
                self.page.locator(betslip_input_selector).first.fill(str(stake))
                time.sleep(0.8)
                
                # --- 5. PIAZZAMENTO E VERIFICA RICEVUTA ---
                if self.allow_place and not test_mode:
                    place_button_selector = ".bs-PlaceBetButton"
                    if self.page.locator(place_button_selector).count() > 0:
                        self.logger.critical(f"🚀 PREMUTO TASTO SCOMMETTI! Attesa conferma dal Bookmaker...")
                        self.page.locator(place_button_selector).first.click(delay=200)
                        
                        # VERIFICA REALE: Attendiamo la ricevuta di Bet365
                        try:
                            # Classi tipiche del messaggio "Scommessa Piazzata" di Bet365
                            receipt_selector = ".bs-ReceiptMessage, .bs-ReceiptContent, .bs-Receipt"
                            self.page.wait_for_selector(receipt_selector, timeout=6000)
                            self.logger.info("✅💰 SCOMMESSA CONFERMATA DAL BOOKMAKER!")
                            return True
                        except:
                            self.logger.error("⚠️ Scommessa cliccata, ma nessuna ricevuta confermata a schermo. Verificare saldo.")
                            return False # Ritorna False per far scattare l'alert di sicurezza dell'engine
                    else:
                        self.logger.error("❌ Bottone 'Scommetti' non trovato nella schedina.")
                        return False
                else:
                    self.logger.warning("🛡️ Modalità TEST attiva (allow_place=False). Scommessa inserita ma NON inviata.")
                    return True
            else:
                self.logger.error("❌ Campo dell'importo nella schedina non trovato.")
                return False

        except Exception as e:
            self.logger.error(f"❌ Errore critico nel protocollo di scommessa: {e}")
            return False
