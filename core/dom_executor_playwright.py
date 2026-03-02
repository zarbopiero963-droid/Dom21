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
        # Traccia in che modalità siamo attualmente (Visibile o Invisibile)
        self.is_visible_mode = False

    def launch_browser(self, headless=True):
        with self._browser_lock:
            # Se il browser è già aperto, controlla se è nella modalità giusta
            if self.context and self.page and not self.page.is_closed():
                if self.is_visible_mode == (not headless):
                    return True # È già corretto, non fare nulla
                else:
                    self._stop_unlocked() # Chiudilo per riaprirlo nella nuova modalità

            try:
                self.playwright = sync_playwright().start()
                self.is_visible_mode = not headless # Aggiorna lo stato
                
                stealth_args = [
                    '--disable-blink-features=AutomationControlled',
                    '--disable-infobars',
                    '--no-sandbox',
                    '--disable-dev-shm-usage',
                    '--disable-gpu',
                    '--ignore-certificate-errors',
                    '--disable-web-security'
                ]
                
                app_data = os.getenv('LOCALAPPDATA', os.path.expanduser('~'))
                user_data_dir = os.path.join(app_data, "SuperAgent_RealProfile")
                os.makedirs(user_data_dir, exist_ok=True)
                
                real_chrome_path = None
                possible_paths = [
                    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
                    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
                    os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"),
                    "/usr/bin/google-chrome"
                ]
                
                for path in possible_paths:
                    if os.path.exists(path):
                        real_chrome_path = path
                        break

                launch_options = {
                    "user_data_dir": user_data_dir,
                    "headless": headless,  # 🔴 ORA È DINAMICO!
                    "args": stealth_args,
                    "viewport": {'width': 1920, 'height': 1080},
                    "user_agent": 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                    "bypass_csp": True,
                    "java_script_enabled": True,
                    "locale": 'it-IT',
                    "timezone_id": 'Europe/Rome'
                }

                if real_chrome_path:
                    launch_options["executable_path"] = real_chrome_path

                self.context = self.playwright.chromium.launch_persistent_context(**launch_options)
                
                stealth_js = """
                    Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
                    window.chrome = { runtime: {} };
                    Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5] });
                    Object.defineProperty(navigator, 'mimeTypes', { get: () => [1, 2, 3, 4] });
                    const getParameter = WebGLRenderingContext.prototype.getParameter;
                    WebGLRenderingContext.prototype.getParameter = function(parameter) {
                        if (parameter === 37445) return 'Intel Inc.';
                        if (parameter === 37446) return 'Intel Iris OpenGL Engine';
                        return getParameter(parameter);
                    };
                    const originalQuery = window.navigator.permissions.query;
                    window.navigator.permissions.query = (parameters) => (
                        parameters.name === 'notifications' ?
                            Promise.resolve({ state: Notification.permission }) :
                            originalQuery(parameters)
                    );
                """
                
                self.context.add_init_script(stealth_js)
                
                if len(self.context.pages) > 0:
                    self.page = self.context.pages[0]
                else:
                    self.page = self.context.new_page()
                    
                return True
            except Exception as e:
                self.logger.error(f"Errore lancio browser: {e}")
                self._stop_unlocked()
                return False

    def _stop_unlocked(self):
        """Chiude tutto senza usare il lock (per uso interno)."""
        try:
            if self.context: self.context.close()
            if self.playwright: self.playwright.stop()
        except: pass
        finally: self.context = self.playwright = self.page = None

    def stop(self):
        with self._browser_lock:
            self._stop_unlocked()

    def close(self):
        self.stop()
        
    def recycle_browser(self):
        self.stop()
        return self.launch_browser(headless=True) # Ricicla sempre in headless

    # =========================================================================
    # 🛡️ ZERO-TOUCH RECOVERY: L'AUTOPILOTA DELLA SESSIONE
    # =========================================================================
    
    def manual_login_window(self, url="https://www.google.com"):
        """Apre il browser a schermo, aspetta che l'utente logghi e chiuda la finestra."""
        self.logger.warning("🖥️ Apertura Browser in Modalità Visibile per Login Manuale...")
        self.stop() # Spegne la modalità invisibile
        time.sleep(1)
        
        success = self.launch_browser(headless=False) # Apre a schermo!
        if success and self.page:
            try:
                self.page.goto(url)
                self.logger.info("⏳ BROWSER APERTO! Fai il login a schermo. Quando hai finito, CHIUDI LA FINESTRA con la 'X'.")
                
                # Il bot si congela qui e aspetta che tu chiuda fisicamente il browser
                self.page.wait_for_event("close", timeout=0) 
                
            except Exception as e:
                self.logger.error(f"Finestra chiusa forzatamente: {e}")
            
            self.logger.info("🔄 Finestra chiusa dall'utente. Ritorno alla modalità Fantasma (Invisibile)...")
            self.stop()
            self.launch_browser(headless=True) # Torna in background
            return True
        return False

    def auto_check_session(self, url, logged_in_selector, login_btn_selector):
        """
        IL CERVELLO: Controlla se siamo loggati. Se no, fa scattare l'apertura a schermo da solo.
        Esempio di utilizzo: auto_check_session("https://bookmaker.it", ".saldo-utente", ".btn-login")
        """
        with self._browser_lock:
            if not self.page or self.page.is_closed():
                return False
                
        try:
            self.page.goto(url, timeout=30000)
            time.sleep(3) # Aspetta che il sito carichi
            
            # 1. Trova l'elemento che prova che siamo loggati (es. il tuo Saldo)
            if self.page.locator(logged_in_selector).count() > 0:
                self.logger.info("✅ Auto-Check: Sessione valida. Procedo in background.")
                return True
            
            # 2. Trova il pulsante "Accedi" -> Siamo stati buttati fuori!
            if self.page.locator(login_btn_selector).count() > 0 or self.page.locator(logged_in_selector).count() == 0:
                self.logger.critical("🚨 Auto-Check: SESSIONE SCADUTA! Avvio procedura Zero-Touch Recovery...")
                
                # Fa aprire Chrome sul tuo schermo in automatico!
                self.manual_login_window(url=url)
                return True # Assume che l'utente abbia risolto prima di chiudere
                
        except Exception as e:
            self.logger.error(f"Errore Auto-Check sessione: {e}")
            return False

    # =========================================================================

    def place_bet(self, teams, market, stake): 
        hook = self._chaos_hooks
        if hook.get("crash_pre_click"): raise ConnectionError("CHAOS SIMULATION: Crash Pre-Click (Internet down)")
        result = True
        if "place_bet" in hook: result = hook["place_bet"](teams, market, stake)
        if hook.get("crash_post_click"): raise ConnectionError("CHAOS SIMULATION: Crash Post-Click (Timeout post conferma)")
        return result

    def check_health(self):
        with self._browser_lock:
            if not self.context or not self.page or self.page.is_closed(): return False
            try: 
                self.page.evaluate("1", timeout=2000)
                return True
            except: 
                return False

    def get_balance(self):
        try:
            if "get_balance" in self._chaos_hooks: return self._chaos_hooks["get_balance"]()
            if hasattr(self, "_get_balance_internal"): return self._get_balance_internal()
            if hasattr(self, "balance"): return float(self.balance)
            return 1000.0  
        except Exception as e:
            self.logger.error(f"Errore lettura saldo: {e}")
            return 0.0
