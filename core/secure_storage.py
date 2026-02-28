import os
import zipfile
import time
import logging
import threading
from pathlib import Path

class SecureStorage:
    def __init__(self, logger=None):
        self.logger = logger or logging.getLogger("SecureStorage")
        self.data_dir = os.path.join(str(Path.home()), ".superagent_data")
        self.backup_dir = os.path.join(self.data_dir, "backups")
        self._io_lock = threading.RLock()
        os.makedirs(self.backup_dir, exist_ok=True)

    def create_snapshot(self):
        with self._io_lock:
            try:
                zip_name = os.path.join(self.backup_dir, f"snapshot_{int(time.time())}.zip")
                backup_dir_abs = os.path.abspath(self.backup_dir)
                
                with zipfile.ZipFile(zip_name, 'w', zipfile.ZIP_DEFLATED) as zipf:
                    for root, _, files in os.walk(self.data_dir):
                        if os.path.abspath(root).startswith(backup_dir_abs): continue
                        for file in files:
                            if file in [".master.key", ".device.salt"] or file.endswith(".bak"): continue
                            file_path = os.path.join(root, file)
                            zipf.write(file_path, os.path.relpath(file_path, self.data_dir))
                self._rotate_backups()
                return True
            except: return False

    def _rotate_backups(self, keep=48):
        try:
            backups = sorted([os.path.join(self.backup_dir, f) for f in os.listdir(self.backup_dir) if f.endswith('.zip')], key=os.path.getmtime)
            while len(backups) > keep: os.remove(backups.pop(0))
        except: pass