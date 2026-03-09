# Questo file indica a Python che la cartella 'ui' è un package.
# Anche se è vuoto, è ESSENZIALE per PyInstaller e per gli import.

# Forziamo l'importazione di tutti i moduli interni al momento dell'inizializzazione
# del pacchetto 'ui'. Questo risolve i problemi di ModuleNotFoundError quando
# l'applicazione viene compilata in un eseguibile (.exe).

try:
    from . import desktop_app
    from . import bookmaker_tab
    from . import selectors_tab
    from . import robots_tab
    from . import anti_detect_tab
    from . import god_certification_tab
    from . import history_tab
    from . import roserpina_tab
except ImportError as e:
    # Se fallisce l'import relativo (es. esecuzione anomala degli script), 
    # proviamo l'import assoluto come fallback
    import logging
    logging.getLogger(__name__).warning(f"⚠️ Fallito import relativo in ui/__init__.py, tento import assoluto. Errore: {e}")
    try:
        import ui.desktop_app
        import ui.bookmaker_tab
        import ui.selectors_tab
        import ui.robots_tab
        import ui.anti_detect_tab
        import ui.god_certification_tab
        import ui.history_tab
        import ui.roserpina_tab
    except ImportError as e_abs:
         logging.getLogger(__name__).error(f"❌ Fallito import assoluto in ui/__init__.py: {e_abs}")
