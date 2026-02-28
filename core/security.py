import os
import platform
import getpass
import logging
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64
from pathlib import Path

class SecurityModule:
    def __init__(self, logger=None):
        self.logger = logger or logging.getLogger("Security")
        self._cached_fernet = None
        self.salt_path = os.path.join(str(Path.home()), ".superagent_data", ".device.salt")

    def _get_machine_fingerprint(self):
        if os.environ.get("CI_BYPASS_SECURITY") == "1": return b"CI_MOCK_FINGERPRINT_123"
        try: return f"{platform.node()}_{getpass.getuser()}_{platform.system()}_{platform.machine()}".encode('utf-8')
        except: return b"FALLBACK_MACHINE_ID"

    def _get_or_create_salt(self):
        if os.path.exists(self.salt_path):
            with open(self.salt_path, "rb") as f: return f.read()
        new_salt = os.urandom(16)
        os.makedirs(os.path.dirname(self.salt_path), exist_ok=True)
        with open(self.salt_path, "wb") as f: f.write(new_salt)
        return new_salt

    def _get_fernet(self):
        if self._cached_fernet: return self._cached_fernet
        kdf = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=self._get_or_create_salt(), iterations=390000)
        self._cached_fernet = Fernet(base64.urlsafe_b64encode(kdf.derive(self._get_machine_fingerprint())))
        return self._cached_fernet

    def encrypt(self, data: str) -> str:
        try: return self._get_fernet().encrypt(data.encode('utf-8')).decode('utf-8')
        except: return ""

    def decrypt(self, token: str) -> str:
        try: return self._get_fernet().decrypt(token.encode('utf-8')).decode('utf-8')
        except Exception as e:
            self.logger.critical(f"FATAL DECRYPT: Hardware modificato. ({e})")
            return ""

# ------------------------------------------------------------------
# 🔁 Backward Compatibility Layer
# ------------------------------------------------------------------
# Vecchi moduli (come tester_v4.py) si aspettano `Vault`.
# Mappiamo l'alias direttamente sulla nuova classe blindata.
Vault = SecurityModule