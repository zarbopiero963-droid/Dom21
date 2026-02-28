import sys
import os
from pathlib import Path

# Supporto eseguibile Frozen (PyInstaller). Previene write-error in directory read-only.
if getattr(sys, 'frozen', False):
    ROOT_DIR = Path.home() / ".superagent_data"
else:
    ROOT_DIR = Path(__file__).parent.parent.resolve()

CONFIG_DIR = ROOT_DIR / "config"
DATA_DIR = ROOT_DIR / "data"

os.makedirs(CONFIG_DIR, exist_ok=True)
os.makedirs(DATA_DIR, exist_ok=True)