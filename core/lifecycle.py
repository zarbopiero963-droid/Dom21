import time
import psutil
import threading
from PySide6.QtCore import QObject, Signal

class SystemWatchdog(QObject):
    alert = Signal(str)

    def __init__(self, logger):
        super().__init__()
        self.logger = logger
        self.running = False
        self.thread = None

    def start(self):
        self.running = True
        self.thread = threading.Thread(target=self._loop, daemon=True, name="Watchdog")
        self.thread.start()

    def _loop(self):
        while self.running:
            try:
                if psutil.virtual_memory().percent > 90:
                    self.alert.emit(f"CRITICAL: Sistema RAM >90%")

                for p in psutil.process_iter(['name', 'memory_info']):
                    try:
                        n = (p.info['name'] or '').lower()
                        if 'chrome' in n or 'chromium' in n:
                            mem_mb = p.info['memory_info'].rss / (1024 * 1024)
                            if mem_mb > 1500:
                                self.alert.emit(f"WARNING: Processo {n} occupa {mem_mb:.0f}MB")
                    except: pass
            except: pass
            time.sleep(30)

    def stop(self):
        self.running = False