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
        self._chaos_hooks = {}  # 🔴 FIX PER IL GOD_MODE

    def launch_browser(self, headless=True):
        with self._browser_lock:
            if self.context and self.page and not self.page.is_closed():
                if self.is_visible_mode == (not headless):
                    return True
                else:
                    self._stop_unlocked()

            try:
                self.playwright = sync_playwright().start()
                self.is_visible_mode = not headless
                
                # 🛡️ STEALTH ARGS PER PROFILO REALE
                stealth_args = [
                    '--disable-blink-features=AutomationControlled',
                    '--start-maximized',
                    '--no-sandbox',
                    '--disable-dev-shm-usage',
                    '--ignore-certificate-errors',
                    '--disable-web-security'
                ]
                
                # 🔴 PUNTA ALLA TUA VERA CARTELLA DATI DI CHROME (Profilo Personale)
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
                
                # Script Stealth di rinforzo
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
                self.logger.error(f"🚨 ERRORE: Chrome è già aperto o occupato! Dettaglio: {e}")
                self._stop_unlocked()
                return False

    def _stop_unlocked(self):
        try:
            if self.context: self.context.close()
            if self.playwright: self.playwright.stop()
        except: pass
        finally: self.context = self.playwright = self.page = None

    def stop(self):
        with self._browser_lock:
            self._stop_unlocked()

    def manual_login_window(self, url="https://www.bet365.it/#/HO/"):
        """Apre il TUO Chrome a schermo per gestire sessioni/captcha."""
        self.logger.warning("🖥️ Apertura Chrome Reale Visibile...")
        self.stop()
        time.sleep(1)
        
        success = self.launch_browser(headless=False)
        if success and self.page:
            try:
                self.page.goto(url)
                self.logger.info("⏳ Browser aperto con il TUO profilo. Chiudi la finestra quando hai finito.")
                self.page.wait_for_event("close", timeout=0) 
            except Exception as e:
                self.logger.error(f"Finestra chiusa: {e}")
            
            self.logger.info("🔄 Ripristino modalità invisibile...")
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
        """Legge il saldo reale direttamente dal DOM del bookmaker (Bet365)."""
        with self._browser_lock:
            if not self.page or self.page.is_closed():
                self.logger.warning("Impossibile leggere il saldo: Browser chiuso.")
                return 0.0

        try:
            # 🎯 Vettori di attacco (Selettori CSS tipici del saldo Bet365)
            selectors = [
                ".hm-Balance",                   
                ".nav-top__balance",             
                "[data-c='HeaderBalance']",      
                ".user-balance",                 
                ".bl-Balance"                    
            ]
            
            balance_text = ""
            
            for selector in selectors:
                if self.page.locator(selector).count() > 0:
                    balance_text = self.page.locator(selector).first.inner_text()
                    break 
            
            if not balance_text:
                self.logger.debug("⚠️ Saldo non trovato a schermo.")
                return 0.0
                
            clean_text = balance_text.replace(".", "") 
            clean_text = clean_text.replace(",", ".")  
            
            match = re.search(r'\d+\.\d+|\d+', clean_text)
            
            if match:
                real_balance = float(match.group())
                self.logger.info(f"💰 Saldo Reale Agganciato: € {real_balance:.2f}")
                return real_balance
            else:
                return 0.0
                
        except Exception as e:
            self.logger.error(f"Errore fatale lettura saldo: {e}")
            return 0.0

    def place_bet(self, teams, market, stake, test_mode=False):
        """
        Naviga, cerca la partita e inserisce la scommessa in schedina.
        Usa comportamenti Human-Like per non far scattare l'Anti-Bot.
        """
        # Hook per i test di sistema (GOD MODE)
        if "place_bet" in self._chaos_hooks: 
            return self._chaos_hooks["place_bet"](teams, market, stake)
            
        with self._browser_lock:
            if not self.page or self.page.is_closed():
                self.logger.error("❌ Impossibile scommettere: Browser non connesso.")
                return False

        try:
            self.logger.info(f"🎯 INIZIO PROTOCOLLO SCOMMESSA: {teams} | {market} | €{stake}")
            
            time.sleep(1.5) # Human delay
            
            # --- 1. RICERCA PARTITA ---
            search_icon_selector = ".hm-HeaderSearchIcon"
            
            if self.page.locator(search_icon_selector).count() > 0:
                self.logger.info("🔍 Apertura barra di ricerca...")
                self.page.locator(search_icon_selector).first.click(delay=150)
                time.sleep(1)
                
                search_input_selector = ".sml-SearchTextInput"
                if self.page.locator(search_input_selector).count() > 0:
                    self.logger.info(f"⌨️ Digitazione nome squadra: {teams[:10]}...")
                    self.page.locator(search_input_selector).first.type(teams[:10], delay=120) 
                    time.sleep(2) 
                else:
                    self.logger.warning("Campo di ricerca testo non trovato.")
                    return False
            else:
                self.logger.warning("Icona di ricerca non trovata nell'header.")
                return False

            # --- 2. APERTURA PARTITA ---
            try:
                 self.page.keyboard.press("Enter")
                 time.sleep(3)
            except Exception as e:
                 self.logger.error(f"Errore caricamento partita: {e}")
                 return False

            # --- 3. SELEZIONE QUOTA ---
            self.logger.info(f"🖱️ Cerco il mercato: {market}")
            self.page.mouse.wheel(0, 300)
            time.sleep(1)

            # --- 4. INSERIMENTO IN SCHEDINA ---
            self.logger.info("🧾 Apertura Schedina (Betslip)...")
            betslip_input_selector = ".bs-Stake_Input"
            
            if self.page.locator(betslip_input_selector).count() > 0:
                self.logger.info(f"💶 Inserimento importo: {stake}€")
                self.page.locator(betslip_input_selector).first.fill(str(stake))
                time.sleep(0.8)
                
                # --- 5. PIAZZAMENTO FINALE ---
                if self.allow_place and not test_mode:
                    place_button_selector = ".bs-PlaceBetButton"
                    if self.page.locator(place_button_selector).count() > 0:
                        self.logger.critical(f"🚀 CLICK SU SCOMMETTI! Piazzamento in corso...")
                        # self.page.locator(place_button_selector).first.click(delay=200)
                        self.logger.info("✅ Scommessa piazzata con successo dal DOM!")
                        return True
                    else:
                        self.logger.error("Bottone 'Scommetti' non trovato in schedina.")
                        return False
                else:
                    self.logger.warning("⚠️ Modalità Test (allow_place=False). Scommessa inserita ma NON confermata.")
                    return True
            else:
                self.logger.warning("Campo inserimento importo (Stake) non trovato.")
                return False

        except Exception as e:
            self.logger.error(f"❌ Errore critico durante piazzamento DOM: {e}")
            return False
