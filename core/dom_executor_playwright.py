import threading
import logging
from playwright.sync_api import sync_playwright

class DomExecutorPlaywright:
    def __init__(self, logger=None, allow_place=False):
        self.logger = logger or logging.getLogger("DomExecutor")
        self.allow_place = allow_place
        self.playwright = self.browser = self.context = self.page = None
        self._browser_lock = threading.Lock()

    def launch_browser(self):
        with self._browser_lock:
            if self.browser and self.browser.is_connected(): return True
            try:
                self.playwright = sync_playwright().start()
                self.browser = self.playwright.chromium.launch(headless=True)
                self.context = self.browser.new_context()
                self.page = self.context.new_page()
                return True
            except:
                self.stop()
                return False

    def stop(self):
        with self._browser_lock:
            try:
                if self.context: self.context.close()
                if self.browser: self.browser.close()
                if self.playwright: self.playwright.stop()
            except: pass
            finally: self.context = self.browser = self.playwright = None

    def place_bet(self, teams, market, stake): return True

    def check_health(self):
        with self._browser_lock:
            if not self.browser or not self.browser.is_connected(): return False
            if self.page:
                try: self.page.evaluate("1", timeout=2000)
                except: return False
        return True