import sys
import os
import random
import sqlite3
import time
import logging

current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = current_dir
while not os.path.exists(os.path.join(project_root, "core")) and project_root != "/":
    project_root = os.path.dirname(project_root)
if project_root not in sys.path: sys.path.insert(0, project_root)

from core.controller import SuperAgentController
from core.database import Database

CHAOS_SEED = 42
random.seed(CHAOS_SEED)

# --- Mocking per bypassare Playwright ma testare l'infrastruttura DB/Risk ---
def create_mock_controller():
    logging.basicConfig(level=logging.CRITICAL)
    c = SuperAgentController(logging.getLogger("GOD_MODE_V2"))
    
    # Bypass Playwright
    c.worker.executor.place_bet = lambda *a, **k: True
    c.worker.executor.navigate_to_match = lambda *a, **k: True
    c.worker.executor.find_odds = lambda *a, **k: 2.0
    c.worker.executor.ensure_login = lambda *a, **k: True
    c.worker.executor.get_balance = lambda *a, **k: c.money_manager.bankroll()
    
    # Forza stato attivo per i test
    c.engine.betting_enabled = True
    c.is_running = True
    return c

def execute_signal(controller, teams):
    """Simula il passaggio del segnale attraverso il motore."""
    payload = {"teams": teams, "market": "1", "raw_text": teams, "stake": 2.0, "mm_mode": "Stake Fisso", "is_active": True}
    controller.engine.process_signal(payload, controller.money_manager)

# --- Iniettori di Caos ---
def simulate_disk_full(*args, **kwargs):
    raise sqlite3.OperationalError("database or disk is full")

def simulate_sqlite_lock(*args, **kwargs):
    raise sqlite3.OperationalError("database is locked")

def inject_crash_pre_bet(executor, original_method):
    def fake_place(*a, **k):
        raise RuntimeError("CHAOS: crash before place_bet")
    executor.place_bet = fake_place

def inject_crash_post_bet(executor, original_method):
    def fake_place(*a, **k):
        original_method(*a, **k) # Simula successo
        raise RuntimeError("CHAOS: crash after place_bet")
    executor.place_bet = fake_place

# --- Auditing Finanziario ---
def financial_audit(db: Database):
    balance, _ = db.get_balance()
    pending = [r for r in db.pending() if r['status'] == 'RESERVED'] # Nel nuovo sistema i pending sono i RESERVED
    placed = db.get_unsettled_placed()

    print(f"[AUDIT] Balance: €{balance:.2f}")
    print(f"[AUDIT] RESERVED (Pending): {len(pending)}")
    print(f"[AUDIT] PLACED: {len(placed)}")

    # 1️⃣ Pending after reboot = fail
    if pending:
        raise AssertionError(f"FAIL: {len(pending)} RESERVED tx survived crash. 2PC Bootloader failed!")

    # 2️⃣ Balance cannot be negative
    if balance < 0:
        raise AssertionError("FAIL: Negative bankroll")

    print("[AUDIT] CONSISTENT\n")

# --- LE 6 FASI DELL'APOCALISSE ---

def test_crash_pre_bet():
    print("=== PHASE 1: CRASH PRE BET (Simula errore bookmaker o crash prima di inviare) ===")
    c = create_mock_controller()
    inject_crash_pre_bet(c.worker.executor, c.worker.executor.place_bet)

    try:
        execute_signal(c, "Milan - Roma")
    except RuntimeError: pass

    financial_audit(c.db)

def test_crash_post_bet():
    print("=== PHASE 2: CRASH POST BET (Simula crash appena il bookmaker accetta) ===")
    c = create_mock_controller()
    inject_crash_post_bet(c.worker.executor, c.worker.executor.place_bet)

    try:
        execute_signal(c, "Inter - Napoli")
    except RuntimeError: pass

    financial_audit(c.db)

def test_disk_full_mark_placed():
    print("=== PHASE 3: DISK FULL DURING MARK_PLACED (Simula I/O fallito durante la Fase 2 del 2PC) ===")
    c1 = create_mock_controller()
    original_mark = c1.db.mark_placed
    c1.db.mark_placed = simulate_disk_full

    try:
        execute_signal(c1, "Lazio - Juve")
    except sqlite3.OperationalError: pass
    finally:
        c1.db.mark_placed = original_mark # Restore

    # Simula Reboot per far scattare il Panic Ledger Recovery
    print("[SYSTEM] Simulating hard reboot to test OS-Level Panic Ledger...")
    c2 = create_mock_controller() 
    
    financial_audit(c2.db)

def test_sqlite_lock():
    print("=== PHASE 4: SQLITE LOCK (Simula collisione thread durante Fase 2) ===")
    c1 = create_mock_controller()
    original_mark = c1.db.mark_placed
    c1.db.mark_placed = simulate_sqlite_lock

    try:
        execute_signal(c1, "Bologna - Torino")
    except sqlite3.OperationalError: pass
    finally:
        c1.db.mark_placed = original_mark

    # 🚑 FIX: Come per il disco pieno, se il DB si blocca dobbiamo simulare il riavvio
    # per permettere al Panic Ledger di essere letto dal Bootloader!
    print("[SYSTEM] Simulating hard reboot to test OS-Level Panic Ledger...")
    c2 = create_mock_controller() 
    
    financial_audit(c2.db)

def test_reboot_with_placed():
    print("=== PHASE 5: REBOOT WITH PLACED (Simula riavvio server con scommesse in corso) ===")
    c1 = create_mock_controller()
    execute_signal(c1, "Atalanta - Fiorentina") # Questa andrà a buon fine e diventerà PLACED
    
    # Simulate Reboot (Ricreando il controller, scatta il bootloader)
    print("[SYSTEM] Simulating hard reboot...")
    c2 = create_mock_controller() 
    
    placed = c2.db.get_unsettled_placed()
    if not placed:
        raise AssertionError("FAIL: PLACED disappeared after reboot. Fatal accounting loss!")

    print(f"[BOOT] OK: {len(placed)} PLACED survived reboot correctly")
    financial_audit(c2.db)

def test_drift():
    print("=== PHASE 6: DRIFT TEST (Simula iniezione fondi esterni) ===")
    db = Database()
    before, _ = db.get_balance()

    db.update_bankroll(before + 50)
    after, _ = db.get_balance()

    if after <= before:
        raise AssertionError("FAIL: Drift not applied")

    print(f"[DRIFT] OK: External bankroll change detected. (Before: {before}, After: {after})")
    print("[AUDIT] CONSISTENT\n")

def run_all():
    print("\n" + "🔥" * 50)
    print("GOD MODE V2 CHAOS ENGINE — HEDGE FUND EDITION")
    print("🔥" * 50 + "\n")
    
    # Assicuriamoci che il DB parta pulito per i test
    db = Database()
    db.conn.execute("DELETE FROM journal")
    db.conn.commit()

    test_crash_pre_bet()
    test_crash_post_bet()
    test_disk_full_mark_placed()
    test_sqlite_lock()
    test_reboot_with_placed()
    test_drift()

    print("============================================================")
    print("👑 GOD MODE V2 PASSED – SYSTEM SURVIVES INFRASTRUCTURE CHAOS")
    print("============================================================\n")

if __name__ == "__main__":
    run_all()
