import time
import threading
import socket

class HealthMonitor:
    def __init__(self, logger):
        self.logger = logger
        self.restart_lock = threading.Lock()
        self.last_restart = 0
        self.cooldown = 60
        self.max_restarts = 5
        self.restart_count = 0

    def check_internet(self):
        hosts = [("8.8.8.8", 53), ("1.1.1.1", 53)]
        for host, port in hosts:
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.settimeout(3)
                    s.connect((host, port))
                return True
            except: continue
        return False

    def can_restart(self):
        with self.restart_lock:
            now = time.time()
            if now - self.last_restart < self.cooldown: return False
            if self.restart_count >= self.max_restarts: return False
            self.last_restart = now
            self.restart_count += 1
            return True

    def reset_counters(self):
        with self.restart_lock: self.restart_count = 0