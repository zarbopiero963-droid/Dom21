import os
import sys

def resource_path(relative_path):
    """ 
    Ottiene il percorso assoluto della risorsa.
    Compatibile con l'eseguibile compresso --onefile generato da GitHub Actions.
    """
    try:
        # PyInstaller estrae i file in _MEIPASS a runtime
        base_path = sys._MEIPASS
    except Exception:
        # Esecuzione da sorgente
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)
