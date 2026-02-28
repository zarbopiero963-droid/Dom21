import os
import yaml
import logging
from core.config_paths import CONFIG_DIR

class ConfigLoader:
    def __init__(self):
        self.config_path = os.path.join(CONFIG_DIR, "config.yaml")
        self.logger = logging.getLogger("ConfigLoader")

    def load_config(self):
        if not os.path.exists(self.config_path):
            self._create_default()
        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
                return data if data is not None else {}
        except Exception as e:
            self.logger.warning(f"Errore durante il caricamento di config.yaml: {e}. Fallback su default vuoto.")
            return {}

    def _create_default(self):
        default_config = {
            "telegram": {"api_id": "", "api_hash": ""},
            "betting": {"allow_place": False},
            "selected_chats": []
        }
        try:
            with open(self.config_path, "w", encoding="utf-8") as f:
                yaml.dump(default_config, f)
        except: pass