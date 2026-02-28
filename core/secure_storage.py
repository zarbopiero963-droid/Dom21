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
                        # 🛡️ FIX 10/10: Controllo deterministico path assoluti
                        if os.path.abspath(root).startswith(backup_dir_abs): 
                            continue
                            
                        for file in files:
                            # Blacklist assoluta layer crittografico
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


class BookmakerManager:
    """
    Gestore sicuro delle credenziali Bookmaker.
    Si appoggia al SecurityModule (Hardware Bound + Dynamic Salt) per la crittografia.
    """
    def __init__(self, logger=None):
        self.logger = logger or logging.getLogger("BookmakerManager")
        self.security = SecurityModule(self.logger)
        self.file_path = os.path.join(str(Path.home()), ".superagent_data", "bookmakers.enc")
        self._lock = threading.RLock()

    def save_credentials(self, username, password, bookmaker="default"):
        with self._lock:
            try:
                data = self.load_all()
                data[bookmaker] = {"username": username, "password": password}
                
                raw_json = json.dumps(data)
                encrypted = self.security.encrypt(raw_json)
                
                if encrypted:
                    with open(self.file_path, "w") as f:
                        f.write(encrypted)
                    self.logger.info(f"Credenziali salvate e crittografate per {bookmaker}.")
                    return True
                return False
            except Exception as e:
                self.logger.error(f"Errore salvataggio credenziali: {e}")
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
                self.logger.error(f"Errore caricamento credenziali (corruzione o decrittazione fallita): {e}")
                return {}

    def get_credentials(self, bookmaker="default") -> dict:
        return self.load_all().get(bookmaker, {"username": "", "password": ""})
