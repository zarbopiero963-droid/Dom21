import time
import threading
import logging
import re
import os
import json
import random
import gc
import psutil
from typing import Any
from playwright.sync_api import sync_playwright
from core.human_mouse import HumanMouse
from core.human_behavior import HumanInput
from core.anti_detect import STEALTH_INJECTION_V5

class FatalCaptcha(Exception): pass
class TimeoutFatal(Exception): pass

class DomExecutorPlaywright:
    def __init__(self, logger=None, headless=False, allow_place=False, **kwargs):
        self.logger = logger or logging.getLogger("Executor")
        self.headless = headless
        self.allow_place = allow_place

        self.pw: Any = None
        self.browser: Any = None
        self.context: Any = None
        self.page: Any = None
        self.mouse: Any = None
        self.human_keyboard: Any = None
        
        self._internal_lock = threading.RLock()
        self.start_time = None 
        
        self.bet_count = 0
        self.login_fails = 0
        self.last_recycle_time = time.monotonic() # 🔴 FIX 2.5: Time-based recycle

    def launch_browser(self):
        with self._internal_lock:
            try:
                if self.page and not self.page.is_closed(): return True
                self.logger.info(f"🚀 Launching Browser Stealth (Headless={self.headless})...")
                if not self.pw: self.pw = sync_playwright().start()
                
                self.browser = self.pw.chromium.launch(
                    headless=self.headless, 
                    args=["--no-sandbox", "--disable-blink-features=AutomationControlled", "--disable-dev-shm-usage"],
                    ignore_default_args=["--enable-automation"]
                )
                
                self.context = self.browser.new_context(
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                    viewport={'width': 1920, 'height': 1080}, has_touch=False, is_mobile=False
                )
                
                stealth_js = """
                Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
                Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3]});
                const getParameter = WebGLRenderingContext.getParameter;
                WebGLRenderingContext.prototype.getParameter = function(parameter) {
                    if (parameter === 37445) return 'Intel Inc.';
                    if (parameter === 37446) return 'Intel Iris OpenGL Engine';
                    return getParameter(parameter);
                };
                window.chrome = { runtime: {} };
                Math.random = function() { return Math.random() + 0.0000000000000001; };
                """
                self.context.add_init_script(stealth_js)
                self.context.add_init_script(STEALTH_INJECTION_V5)
                
                self.page = self.context.new_page()
                
                try:
                    self.human_keyboard = HumanInput(self.page, self.logger)
                    self.mouse = HumanMouse(self.page, self.human_keyboard.profile, self.logger)
                except Exception:
                    self.mouse, self.human_keyboard = None, None

                self.start_time = time.monotonic()
                
                try:
                    self.page.goto("https://www.bet365.it", timeout=30000)
                    self.page.wait_for_load_state("domcontentloaded", timeout=15000)
                    self._check_invisible_captcha() # 🔴 FIX 2.3
                except FatalCaptcha: raise
                except Exception as exc: self.logger.warning(f"Home load warning: {exc}")
                    
                return True
            except Exception as exc:
                self.logger.error(f"Critical launch_browser: {exc}")
                self.close()
                return False

    def _check_invisible_captcha(self):
        """🔴 FIX 2.3: Intercetta i Captcha invisibili o i freeze iframe"""
        if not self.page: return
        title = self.page.title().lower()
        if "just a moment" in title or "captcha" in title:
            self.logger.critical("🛑 FATAL CAPTCHA: Intercettata challenge Cloudflare/Datadome.")
            raise FatalCaptcha("Cloudflare challenge bloccante.")
        try:
            html = self.page.content().lower()
            if "cf-challenge" in html:
                raise FatalCaptcha("Cloudflare iframe challenge rilevato.")
        except: pass

    def _stealth_click(self, locator: Any):
        if not self.mouse: locator.click(timeout=10000); return
        self.mouse.click(locator)

    def _stealth_type(self, locator: Any, text: str):
        if not self.human_keyboard: locator.fill(text, timeout=10000); return
        self._stealth_click(locator)
        time.sleep(random.uniform(0.2, 0.5))
        locator.press("Control+a")
        time.sleep(random.uniform(0.1, 0.2))
        locator.press("Backspace")
        time.sleep(random.uniform(0.3, 0.6))
        self.human_keyboard.type_text(text)

    def recycle_browser(self):
        self.logger.warning("🔄 Hard Recycle Browser (Prevenzione Memory Leak V8)...")
        self.close()
        time.sleep(2)
        self.bet_count = 0
        self.last_recycle_time = time.monotonic()
        return self.launch_browser()

    def is_logged(self):
        try:
            if self.page.locator("text='Accedi', text='Login'").count() > 0: return False
            if self.page.locator(".hm-Balance").count() > 0: return True
            return False
        except Exception: return False

    def ensure_login(self, account_id="bet365_main"):
        if not self.launch_browser(): return False
        try:
            if self.is_logged(): return True
            self.logger.info(f"🔑 Login Umano: {account_id}...")
            from core.secure_storage import BookmakerManager
            username, password = BookmakerManager().get_decrypted(account_id)
            if not username or not password: return False

            login_btn = self.page.locator(".hm-MainHeaderRHSLoggedOutWide_Login, text='Login', text='Accedi'").first
            if login_btn.is_visible(timeout=10000):
                self._stealth_click(login_btn)
                self.page.wait_for_timeout(2000)

            self._stealth_type(self.page.locator(".lms-StandardLogin_Username, input[type='text']").first, username)
            self._stealth_type(self.page.locator(".lms-StandardLogin_Password, input[type='password']").first, password)
            time.sleep(random.uniform(0.5, 1.2))
            self._stealth_click(self.page.locator(".lms-LoginButton").first)
            self.page.wait_for_selector(".hm-Balance", timeout=20000)
            self.login_fails = 0
            return True
        except Exception as exc:
            self.login_fails += 1
            return False

    def navigate_to_match(self, teams, is_live=True):
        if not self.launch_browser() or not self.ensure_login(): return False
        try:
            search_btn = self.page.locator(".hm-MainHeaderCentreWide_SearchIcon, .hm-MainHeader_SearchIcon").first
            if search_btn.is_visible(timeout=15000): self._stealth_click(search_btn)
            self.page.wait_for_timeout(1500)
            
            team_a = teams.split("-")[0].strip().lower() if "-" in teams else teams.strip().lower()
            self._stealth_type(self.page.locator("input.hm-MainHeaderCentreWide_SearchInput, input.sml-SearchInput").first, team_a)
            self.page.wait_for_timeout(random.randint(2500, 4000)) 

            results = self.page.locator(".sml-SearchParticipant_Name, .sml-EventParticipant, .sml-Result")
            if results.count() > 0:
                self._stealth_click(results.first)
                self.page.wait_for_load_state("domcontentloaded", timeout=15000)
                self._check_invisible_captcha()
                return True
            return False
        except Exception: return False

    def find_odds(self, teams, market):
        if not self.launch_browser(): return 0.0
        try:
            self.page.wait_for_selector(".gl-MarketGroup", timeout=15000)
            return 2.0 
        except Exception: return 0.0

    def get_balance(self):
        if not self.launch_browser(): return None
        try:
            bal_el = self.page.locator(".hm-Balance").first
            if bal_el.is_visible(timeout=5000):
                txt = bal_el.inner_text().replace("€","").replace("$","").strip().replace(".", "").replace(",", ".")
                try: return float(txt)
                except: return None
            return None
        except Exception: return None

    def check_settled_bets(self): return {"status": None}

    def place_bet(self, teams, market, stake):
        # 🔴 FIX 2.4: Global Deadline per prevenire freeze del job
        deadline = time.monotonic() + 60 

        if not self.launch_browser() or not self.is_logged(): return False

        try:
            # 🔴 FIX 2.5: Recycle ibrido (40 bet o 45 minuti uptime)
            if (self.bet_count > 0 and self.bet_count % 40 == 0) or (time.monotonic() - self.last_recycle_time > 2700):
                if not self.recycle_browser() or not self.ensure_login(): return False

            if time.monotonic() > deadline: raise TimeoutFatal("Deadline globale 60s scaduta in pre-bet")

            saldo_pre = self.get_balance()
            if saldo_pre is None or saldo_pre < stake: return False

            odds_btn = self.page.locator(".gl-Participant_Odds").first
            if not odds_btn.is_visible(timeout=10000): return False
            self._stealth_click(odds_btn)
            
            self.page.wait_for_selector(".bs-BetSlip", timeout=15000)
            time.sleep(random.uniform(0.8, 1.5))

            if time.monotonic() > deadline: raise TimeoutFatal("Deadline globale scaduta su bet slip")

            self._stealth_type(self.page.locator("input.bs-Stake_Input, input.st-Stake_Input").first, str(stake))
            time.sleep(random.uniform(0.6, 1.3))

            if self.allow_place:
                place_btn = self.page.locator("button.bs-PlaceBetButton, button.st-PlaceBetButton").first
                if place_btn.is_enabled():
                    self._stealth_click(place_btn)
                    self.page.wait_for_selector(".bs-Receipt, .st-Receipt", timeout=20000)
                    self._check_invisible_captcha()
                    self.bet_count += 1
                    return True
                return False
            else:
                self.bet_count += 1
                return True
        except FatalCaptcha:
            self.logger.critical("Esecuzione abortita per Captcha.")
            return False
        except Exception as e:
            self.logger.error(f"Errore piazzamento: {e}")
            return False

    def close(self):
        # 🔴 FIX 2.1 e 2.2: Hard close + GC + Psutil Zombie Kill
        try:
            if self.page: self.page.close()
            if self.context: self.context.close()
            if self.browser: self.browser.close()
            if self.pw: self.pw.stop()
        except Exception: pass
        
        self.page = self.context = self.browser = self.pw = None
        
        gc.collect() # Forza garbage collector di Python
        
        # Sterminio zombie Chromium
        for p in psutil.process_iter(['name']):
            try:
                n = (p.info['name'] or '').lower()
                if 'chromium' in n or 'chrome' in n: p.kill()
            except: pass