import sys
from pathlib import Path

def get_app_root() -> Path:
    """
    Root unica dell'applicazione.
    Compatibile con sviluppo locale e PyInstaller.
    """
    if getattr(sys, "frozen", False):
        return Path.home() / ".superagent_data"
    return Path(__file__).parent.parent.resolve()


APP_ROOT = get_app_root()
CONFIG_DIR = APP_ROOT / "config"

# File di configurazione principali
CONFIG_FILE = CONFIG_DIR / "config.yaml"
ROBOTS_FILE = CONFIG_DIR / "robots.yaml"
SELECTORS_FILE = CONFIG_DIR / "selectors.yaml"
ROSERPINA_SETTINGS_FILE = CONFIG_DIR / "roserpina_settings.yaml"