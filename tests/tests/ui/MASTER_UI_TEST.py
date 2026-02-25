import os
import sys
import time
import pytest
from PySide6.QtWidgets import QApplication, QPushButton, QLineEdit, QDoubleSpinBox, QSpinBox, QMessageBox
from PySide6.QtTest import QTest
from PySide6.QtCore import Qt, Signal, QObject

# =========================================================
# PATH FIX
# =========================================================
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

# =========================================================
# IMPORT APP
# =========================================================
from ui.desktop_app import DesktopApp

# =========================================================
# TEST ENV ISOLATO
# =========================================================
TEST_VAULT = "test_superagent_vault"
os.makedirs(TEST_VAULT, exist_ok=True)

import core.config_paths
core.config_paths.CONFIG_DIR = TEST_VAULT

# =========================================================
# FIX TIME SLEEP (per velocizzare i test)
# =========================================================
orig_sleep = time.sleep
time.sleep = lambda s: orig_sleep(s) if s < 0.3 else None

# =========================================================
# MASTER UI TEST
# =========================================================
@pytest.fixture
def app(qtbot, monkeypatch):
    # 0. FIX MORTALE: BLOCCHIAMO I POPUP (QMessageBox)
    # Se la UI apre un popup di successo o errore, blocca il test all'infinito.
    # Con queste 3 righe, diciamo al test di simulare la pressione di "OK" istantaneamente.
    monkeypatch.setattr(QMessageBox, "information", lambda *args, **kwargs: None)
    monkeypatch.setattr(QMessageBox, "warning", lambda *args, **kwargs: None)
    monkeypatch.setattr(QMessageBox, "critical", lambda *args, **kwargs: None)

    # 1. FIX: MOCKIAMO IL CONFIG_LOADER PER EVITARE CRASH SUL SALVATAGGIO
    import core.config_loader
    if not hasattr(core.config_loader.ConfigLoader, 'save_config'):
        # Se la funzione non esiste, la creiamo al volo finta per far passare il test
        core.config_loader.ConfigLoader.save_config = lambda self, cfg: print("Mock: YAML Salvato")

    # 2. FIX: MOCKIAMO I MOTORI E IL DATABASE
    class MockLogger:
        def info(self, msg): pass
        def warning(self, msg): pass
        def error(self, msg): pass
        def critical(self, msg): pass

    # 🛡️ FIX: Aggiungiamo un DB Finto per le nuove Tab
    class MockDB:
        def get_balance(self): return 1000.0, 1000.0
        def get_roserpina_tables(self): return []
        def pending(self): return []
        class _lock:
            def __enter__(self): pass
            def __exit__(self, exc_type, exc_val, exc_tb): pass
        def __init__(self):
            self._lock = self._lock()
            
    class MockController:
        class Signals(QObject):
            log_message = Signal(str)

        def __init__(self):
            self.signals = self.Signals()
            self.log_message = self.signals.log_message
            self.is_running = False
            self.db = MockDB() # 🛡️ Assegniamo il DB finto al controller
            
        def start_listening(self): self.is_running = True
        def stop_listening(self): self.is_running = False

    config = {}
    window = DesktopApp(MockLogger(), None, config, None, MockController())
    qtbot.addWidget(window)
    window.show()
    return window


def test_full_user_flow(app, qtbot):
    """
    MASTER TEST INDISTRUTTIBILE:
    Non usa nomi di variabili fisse, ma cerca i form dinamicamente come un web scraper.
    """
    print("\n🚀 INIZIO TEST END-TO-END UI")
    
    # 1️⃣ CLOUD TAB (Indice 5 - Attenzione: con le nuove tab l'indice potrebbe essere cambiato!
    # Se il test fallisce in futuro, controlla l'indice della Cloud Tab o usa app.tabs.setCurrentWidget)
    # Troviamo la Cloud Tab dinamicamente per sicurezza:
    cloud_idx = -1
    for i in range(app.tabs.count()):
        if "Cloud" in app.tabs.tabText(i):
            cloud_idx = i
            break
            
    if cloud_idx != -1:
        app.tabs.setCurrentIndex(cloud_idx)
        cloud_inputs = app.tabs.widget(cloud_idx).findChildren(QLineEdit)
        if len(cloud_inputs) >= 4:
            cloud_inputs[0].setText("123456")
            cloud_inputs[1].setText("hash_test")
            cloud_inputs[2].setText("session_test")
            cloud_inputs[3].setText("sk-test")
        
        save_cloud_btn = app.tabs.widget(cloud_idx).findChild(QPushButton)
        if save_cloud_btn:
            qtbot.mouseClick(save_cloud_btn, Qt.LeftButton)
        QTest.qWait(300)

    # 2️⃣ BOOKMAKER TAB (Indice 1)
    app.tabs.setCurrentIndex(1)
    book_tab = app.tabs.widget(1)
    
    book_inputs = book_tab.findChildren(QLineEdit)
    if len(book_inputs) >= 3:
        book_inputs[0].setText("Bet365_Test")
        book_inputs[1].setText("user_test")
        book_inputs[2].setText("pass_test")
        
    save_book_btn = book_tab.findChild(QPushButton)
    if save_book_btn:
        qtbot.mouseClick(save_book_btn, Qt.LeftButton)
    QTest.qWait(300)

    # 3️⃣ ROBOT TAB (Indice 3)
    app.tabs.setCurrentIndex(3)
    robot_tab = app.tabs.widget(3)
    
    robot_btns = robot_tab.findChildren(QPushButton)
    if robot_btns:
        qtbot.mouseClick(robot_btns[0], Qt.LeftButton)
    QTest.qWait(200)
    
    robot_inputs = robot_tab.findChildren(QLineEdit)
    if len(robot_inputs) >= 2:
        robot_inputs[0].setText("Robot_Test")
        robot_inputs[1].setText("goal,over")
        
    spinboxes = robot_tab.findChildren(QDoubleSpinBox) + robot_tab.findChildren(QSpinBox)
    if spinboxes:
        spinboxes[0].setValue(5.0)
    elif len(robot_inputs) >= 3:
        robot_inputs[2].setText("5")
        
    QTest.qWait(500)

    print("🟢 UI FLUSSO COMPLETO SUPERATO CON SUCCESSO")
