import os
import logging
from pathlib import Path
from cryptography.fernet import Fernet

class CryptoVault:
    def __init__(self, logger=None):
        self.logger = logger or logging.getLogger("CryptoVault")
        self.key_path = os.path.join(str(Path.home()), ".superagent_data", ".master.key")
        self._key = self._load_or_create_key()
        self.cipher = Fernet(self._key)

    def _load_or_create_key(self):
        os.makedirs(os.path.dirname(self.key_path), exist_ok=True)
        if os.path.exists(self.key_path):
            with open(self.key_path, "rb") as f:
                return f.read()
        else:
            key = Fernet.generate_key()
            with open(self.key_path, "wb") as f:
                f.write(key)
            return key

    def encrypt(self, plain_text: str) -> str:
        if not plain_text: return ""
        try:
            return self.cipher.encrypt(plain_text.encode('utf-8')).decode('utf-8')
        except Exception as e:
            self.logger.error(f"Encryption failed: {e}")
            return ""

    def decrypt(self, cipher_text: str) -> str:
        if not cipher_text: return ""
        try:
            return self.cipher.decrypt(cipher_text.encode('utf-8')).decode('utf-8')
        except Exception as e:
            self.logger.warning(f"Decryption failed. Data corrupted or Master Key mismatch. Error: {e}")
            return ""