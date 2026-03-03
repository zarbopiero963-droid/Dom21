import threading
import logging
import os
import time
from playwright.sync_api import sync_playwright


class DomExecutorPlaywright:
    def __init__(self, logger=None, allow_place=False):
        self.logger = logger or logging.getLogger("DomExecutor")
        self.allow_place = allow_place
        self.playwright = self.context = self.page = None
        self._browser_lock = threading.Lock()
        self._chaos_hooks = {}
        self.is_visible_mode = False

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
                    "user_data_dir": user_data_path, # 🔴 USA IL TUO PROFILO DEFAULT
                    "headless": headless,
                    "args": stealth_args,
                    "no_viewport": True, # 🔴 RISOLUZIONE NATIVA (Niente cornici finte)
                    "ignore_default_args": ["--enable-automation"], # 🔴 Rimuove "Chrome è controllato da un software..."
                    "bypass_csp": True,
                    "java_script_enabled": True,
                }

                if real_chrome_path:
                    launch_options["executable_path"] = real_chrome_path

                self.logger.info(f"🚀 Avvio Chrome Reale (Headless={headless})...")
                
                # Avviamo il contesto persistente sul tuo profilo reale
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
            import re
            
            # 🎯 Vettori di attacco (Selettori CSS tipici del saldo Bet365)
            # Bet365 cambia spesso le classi HTML per difendersi dai bot. 
            # Noi ne proviamo diverse in cascata finché non lo troviamo.
            selectors = [
                ".hm-Balance",                   # Classe storica Bet365
                ".nav-top__balance",             # Classe header moderno
                "[data-c='HeaderBalance']",      # Attributo React/Angular
                ".user-balance",                 # Classe generica
                ".bl-Balance"                    # Classe alternativa
            ]
            
            balance_text = ""
            
            # Cerca il saldo a schermo senza ricaricare la pagina (invisibile)
            for selector in selectors:
                if self.page.locator(selector).count() > 0:
                    balance_text = self.page.locator(selector).first.inner_text()
                    break # Trovato! Interrompi la ricerca
            
            if not balance_text:
                self.logger.debug("⚠️ Saldo non trovato a schermo. Potresti non essere loggato o essere in una pagina senza header.")
                return 0.0
                
            # 🧹 Pulizia del dato (Regex Hedge-Grade)
            # Trasforma stringhe come "€ 1.234,56" o "Balance: 1234,56 €" -> 1234.56
            clean_text = balance_text.replace(".", "") # Togli i punti delle migliaia
            clean_text = clean_text.replace(",", ".")  # Trasforma le virgole dei decimali in punti (standard Python)
            
            # Estrae solo il numero matematico
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
