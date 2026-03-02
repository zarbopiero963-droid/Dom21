import threading
import logging
import os
from playwright.sync_api import sync_playwright

class DomExecutorPlaywright:
    def __init__(self, logger=None, allow_place=False):
        self.logger = logger or logging.getLogger("DomExecutor")
        self.allow_place = allow_place
        self.playwright = self.context = self.page = None
        self._browser_lock = threading.Lock()
        self._chaos_hooks = {}

    def launch_browser(self):
        with self._browser_lock:
            if self.context and self.page and not self.page.is_closed(): return True
            
            try:
                self.playwright = sync_playwright().start()
                
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
                
                # 🛡️ RICERCA DEL VERO CHROME INSTALLATO SUL PC
                real_chrome_path = None
                possible_paths = [
                    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
                    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
                    os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"),
                    "/usr/bin/google-chrome" # Supporto Linux VPS
                ]
                
                for path in possible_paths:
                    if os.path.exists(path):
                        real_chrome_path = path
                        self.logger.info(f"🚀 Vero Google Chrome rilevato in: {path}")
                        break

                # 🛡️ CONFIGURAZIONE AVVIO
                launch_options = {
                    "user_data_dir": user_data_dir,
                    "headless": True, # Cambia in False se vuoi vederlo a schermo
                    "args": stealth_args,
                    "viewport": {'width': 1920, 'height': 1080},
                    "user_agent": 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                    "bypass_csp": True,
                    "java_script_enabled": True,
                    "locale": 'it-IT',
                    "timezone_id": 'Europe/Rome'
                }

                # Se trova il Chrome vero lo usa, altrimenti usa il Chromium di Playwright
                if real_chrome_path:
                    launch_options["executable_path"] = real_chrome_path
                else:
                    self.logger.warning("⚠️ Chrome reale non trovato, fallback su Chromium integrato.")

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
                self.stop()
                return False

    def stop(self):
        with self._browser_lock:
            try:
                if self.context: self.context.close()
                if self.playwright: self.playwright.stop()
            except: pass
            finally: self.context = self.playwright = self.page = None

    def close(self):
        self.stop()
        
    def recycle_browser(self):
        self.stop()
        return self.launch_browser()

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
