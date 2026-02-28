import os
import zipfile
import time
import logging
import threading
import json
from pathlib import Path
from core.security import SecurityModule

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
                        if os.path.abspath(root).startswith(backup_dir_abs): 
                            continue
                        for file in files:
                            if file in [".master.key", ".device.salt"] or file.endswith(".bak"): 
                                continue
                            file_path = os.path.join(root, file)
                            arcname = os.path.relpath(file_path, self.data_dir)
                            zipf.write(file_path, arcname)
                            
                self.logger.info(f"✅ Snapshot di sicurezza creato: {zip_name}")
                self._rotate_backups()
                return True
            except Exception as e:
                self.logger.error(f"❌ Errore snapshot: {e}")
                return False

    def _rotate_backups(self, keep=48):
        try:
            backups = sorted(
                [os.path.join(self.backup_dir, f) for f in os.listdir(self.backup_dir) if f.endswith('.zip')],
                key=os.path.getmtime
            )
            while len(backups) > keep: 
                os.remove(backups.pop(0))
        except Exception as e:
            self.logger.warning(f"Errore rotazione backup: {e}")


# ==========================================
# UI STORAGE MANAGERS (DRY ARCHITECTURE)
# ==========================================

class BaseSecureManager:
    """Classe base per la gestione sicura e atomica dei dati UI via JSON + Fernet"""
    def __init__(self, filename: str, logger_name: str):
        self.logger = logging.getLogger(logger_name)
        self.security = SecurityModule(self.logger)
        self.file_path = os.path.join(str(Path.home()), ".superagent_data", filename)
        self._lock = threading.RLock()

    def save_data(self, data: dict) -> bool:
        with self._lock:
            try:
                raw_json = json.dumps(data)
                encrypted = self.security.encrypt(raw_json)
                if encrypted:
                    with open(self.file_path, "w") as f:
                        f.write(encrypted)
                    return True
                return False
            except Exception as e:
                self.logger.error(f"Errore salvataggio {self.file_path}: {e}")
                return False

    def load_all(self) -> dict:
        with self._lock:
            if not os.path.exists(self.file_path): 
                return {}
            try:
                with open(self.file_path, "r") as f:
                    encrypted = f.read()
                decrypted = self.security.decrypt(encrypted)
                if decrypted:
                    return json.loads(decrypted)
                return {}
            except Exception as e:
                self.logger.error(f"Errore caricamento {self.file_path}: {e}")
                return {}


class BookmakerManager(BaseSecureManager):
    def __init__(self, logger=None):
        super().__init__("bookmakers.enc", "BookmakerManager")

    def save_credentials(self, username, password, bookmaker="default"):
        data = self.load_all()
        data[bookmaker] = {"username": username, "password": password}
        return self.save_data(data)

    def get_credentials(self, bookmaker="default") -> dict:
        return self.load_all().get(bookmaker, {"username": "", "password": ""})


class SelectorManager(BaseSecureManager):
    def __init__(self, logger=None):
        super().__init__("selectors.enc", "SelectorManager")

    def save_selectors(self, selectors_data: dict):
        return self.save_data(selectors_data)

    def get_selectors(self) -> dict:
        return self.load_all()


class RobotManager(BaseSecureManager):
    def __init__(self, logger=None):
        super().__init__("robots.enc", "RobotManager")

    def save_robots(self, robots_data: dict):
        return self.save_data(robots_data)

    def get_robots(self) -> dict:
        return self.load_all()


class APIKeyManager(BaseSecureManager):
    def __init__(self, logger=None):
        super().__init__("apikeys.enc", "APIKeyManager")

    def save_keys(self, keys_data: dict):
        return self.save_data(keys_data)

    def get_keys(self) -> dict:
        return self.load_all()
