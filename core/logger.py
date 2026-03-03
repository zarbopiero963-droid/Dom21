import logging
import os
import sys
from logging.handlers import RotatingFileHandler

class GUILogHandler(logging.Handler):
    """
    Il 'Ponte'. Intercetta i log di sistema e li spara in tempo reale
    alla funzione della UI (la Tab 10) tramite una callback.
    """
    def __init__(self, callback):
        super().__init__()
        self.callback = callback

    def emit(self, record):
        # Formatta il messaggio
        msg = self.format(record)
        if self.callback:
            try:
                self.callback(msg)
            except Exception:
                pass

def setup_global_logger(ui_callback=None):
    """
    Inizializza la Scatola Nera. Cattura TUTTO ciò che accade nel programma.
    """
    # Prende il logger "root" (il padre di tutti i logger nel programma)
    logger = logging.getLogger()
    
    # Rimuove eventuali vecchi handler per evitare messaggi duplicati
    if logger.hasHandlers():
        logger.handlers.clear()
        
    # LIVELLO DEBUG: Cattura anche il battito d'ali di una mosca
    logger.setLevel(logging.DEBUG) 

    # Formattazione Hacker-Style: Data | Ora | Livello | Modulo | Messaggio
    log_format = '%(asctime)s | %(levelname)-8s | [%(module)s] %(message)s'
    formatter = logging.Formatter(log_format, datefmt='%Y-%m-%d %H:%M:%S')

    # 1. FILE LOGGER (La vera scatola nera su disco)
    # Crea la cartella 'logs' nella root del progetto se non esiste
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    log_dir = os.path.join(base_dir, 'logs')
    os.makedirs(log_dir, exist_ok=True)
    
    file_handler = RotatingFileHandler(
        os.path.join(log_dir, 'superagent_master.log'),
        maxBytes=10*1024*1024, # File da max 10 MB
        backupCount=5,         # Tiene gli ultimi 5 file di log
        encoding='utf-8'
    )
    file_handler.setLevel(logging.DEBUG) # Su file scriviamo TUTTO
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    # 2. CONSOLE LOGGER (Per chi guarda il terminale CMD)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO) # Sul terminale mostriamo solo INFO
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # 3. GUI LOGGER (Per la Tab 10 dell'interfaccia)
    if ui_callback:
        gui_handler = GUILogHandler(ui_callback)
        gui_handler.setLevel(logging.INFO) # Nella UI mostriamo le INFO e i WARNING
        gui_handler.setFormatter(formatter)
        logger.addHandler(gui_handler)

    logger.debug("🟢 Master Logger Inizializzato. Scatola Nera attiva.")
    return logger
