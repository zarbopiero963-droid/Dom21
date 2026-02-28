import os
import time
import logging
import platform
import threading

try:
    import pyautogui
    pyautogui.FAILSAFE = True
    PYAUTOGUI_AVAILABLE = True
except ImportError: PYAUTOGUI_AVAILABLE = False

class OSHumanInteraction:
    def __init__(self, logger=None):
        self.logger = logger or logging.getLogger("OS_Human")
        self._lock = threading.Lock()

    def minimize_all(self):
        if not PYAUTOGUI_AVAILABLE: return
        with self._lock:
            try:
                sys_os = platform.system()
                if sys_os == "Windows": pyautogui.hotkey('win', 'd')
                elif sys_os == "Darwin": pyautogui.hotkey('command', 'f3') 
                time.sleep(1)
            except: pass

    def click_icon_by_image(self, image_path: str):
        if not PYAUTOGUI_AVAILABLE or not os.path.exists(image_path): return False
        with self._lock:
            try:
                try: pos = pyautogui.locateCenterOnScreen(image_path, confidence=0.8)
                except (TypeError, Exception): pos = pyautogui.locateCenterOnScreen(image_path)
                if pos:
                    pyautogui.moveTo(pos.x, pos.y, 0.5, pyautogui.easeOutQuad)
                    time.sleep(0.2)
                    pyautogui.click()
                    return True
                return False
            except: return False