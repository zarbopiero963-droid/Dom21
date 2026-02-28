import time
import logging
import threading
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

class DomExecutorPlaywright:
    def __init__(self, logger=None, allow_place=False):
        self.logger = logger or logging.getLogger("DomExecutor")
        self.allow_place = allow_place
        self.playwright = None
        self.browser = None
        self.context = None
        self.page = None
        
        self._browser_lock = threading.Lock()
        
        self._mock_balance = 1000.0
        self._chaos_hooks = {}

    def launch_browser(self):
        with self._browser_lock:
            if self.browser and self.browser.is_connected(): 
                return True
            try:
                self.playwright = sync_playwright().start()
                self.browser = self.playwright.chromium.launch(headless=True)
                self.context = self.browser.new_context()
                self.page = self.context.new_page()
                return True
            except Exception as e:
                self.logger.error(f"Failed to launch browser: {e}")
                try:
                    if self.context: self.context.close()
                except: pass
                try:
                    if self.browser: self.browser.close()
                except: pass
                if self.playwright:
                    try: self.playwright.stop()
                    except: pass
                    
                self.context = None
                self.page = None
                self.browser = None
                self.playwright = None
                return False

    def stop(self):
        with self._browser_lock:
            try:
                if self.context:
                    self.context.close()
                if self.browser:
                    self.browser.close()
                if self.playwright:
                    self.playwright.stop()
            except Exception as e:
                self.logger.error(f"Error during browser teardown: {e}")
            finally:
                self.context = None
                self.browser = None
                self.playwright = None

    def place_bet(self, teams, market, stake):
        return True
        
    def check_health(self):
        with self._browser_lock:
            if not self.browser or not self.browser.is_connected():
                return False
            # Deep health check: valuta la responsività reale del renderer
            if self.page:
                try:
                    self.page.evaluate("1", timeout=2000)
                except Exception:
                    return False
        return True