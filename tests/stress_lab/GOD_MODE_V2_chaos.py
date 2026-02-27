import sys
import os
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

# --- INIZIALIZZAZIONE AMBIENTE ---
def create_mock_controller():
    logging.basicConfig(level=logging.CRITICAL)
    c = SuperAgentController(logging.getLogger("GOD_MODE_V2"))
    
    # 🧹 Reset Breaker persistente
    if hasattr(c.engine, 'breaker'):
        c.engine.breaker.manual_reset()
    
    # Non sovrascriviamo più place_bet con lambda. Usiamo l'executor istituzionale reale.
    c.worker.executor._mock_logged_in = True
    c.worker.executor._mock_balance = 1000.0
    c.worker.executor.allow_place = True # Per testare il flusso completo
    
    c.engine.betting_enabled = True
    c.is_running = True
    return c

def reset_ledger(c: SuperAgentController):
    """Pulisce il DB e resetta i saldi per avere test isolati."""
    c.db.conn.execute("DELETE FROM journal")
    c.db.conn.execute("UPDATE balance SET current_balance=1000.0, peak_balance=1000.0")
    c.db.conn.commit()
    c.worker.executor._chaos_hooks.clear()
    c.worker.executor._mock_logged_in = True
    c.worker.executor._mock_balance = 1000.0
    if hasattr(c.engine, 'breaker'):
        c.engine.breaker.manual_reset()

def execute_signal(controller, teams):
    payload = {"teams": teams, "market": "1", "raw_text": teams, "stake": 2.0, "mm_mode": "Stake Fisso", "is_active": True}
    controller.engine.process_signal(payload, controller.money_manager)

def strict_audit(db: Database, expected_balance: float, expected_placed: int, expected_manual: int):
    """Verifica matematica dello stato transazionale post-bootloader."""
    balance, _ = db.get_balance()
    journal = [dict(r) for r in db.conn.execute("SELECT * FROM journal").fetchall()]
    
    placed = len([r for r in journal if r['status'] == 'PLACED'])
    manual = len([r for r in journal if r['status'] == 'MANUAL_CHECK'])
    voided = len([r for r in journal if r['status'] == 'VOID'])
    reserved = len([r for r in journal if r['status'] == 'RESERVED'])
    pre_commit = len([r for r in journal if r['status'] == 'PRE_COMMIT'])

    print(f"[AUDIT] Balance: €{balance:.2f} | PLACED: {placed} | MANUAL_CHECK: {manual} | VOID: {voided}")

    if reserved > 0 or pre_commit > 0:
        raise AssertionError(f"FAIL: Transazioni intermedie (RESERVED:{reserved}, PRE_COMMIT:{pre_commit}) sopravvissute al bootloader!")
    
    if balance != expected_balance:
        raise AssertionError(f"FAIL: Balance mismatch. Atteso {expected_balance}, Trovato {balance}")
    
    if placed != expected_placed:
        raise AssertionError(f"FAIL: PLACED mismatch. Atteso {expected_placed}, Trovato {placed}")
        
    if manual != expected_manual:
        raise AssertionError(f"FAIL: MANUAL_CHECK mismatch. Atteso {expected_manual}, Trovato {manual}")

    print("[AUDIT] 🟢 CONSISTENT (Strict Match)\n")

# ==========================================
# 🔥 LE 4 FASI DELLA CERTIFICAZIONE 2PC 🔥
# ==========================================

def test_crash_pre_precommit():
    print("=== PHASE 1: CRASH PRE-PRE_COMMIT (I/O Fail durante la Reserve) ===")
    c = create_mock_controller()
    reset_ledger(c)
    
    # Iniezione errore direttamente su DB prima del PRE_COMMIT
    original_mark = c.db.mark_pre_commit
    def mock_fail(*a, **k): raise sqlite3.OperationalError("I/O Error")
    c.db.mark_pre_commit = mock_fail
    
    try: execute_signal(c, "Match 1")
    except Exception: pass
    finally: c.db.mark_pre_commit = original_mark
    
    # Simuliamo il riavvio per far agire il Bootloader
    c2 = create_mock_controller()
    # Expect: RESERVED è diventato VOID, soldi rimborsati.
    strict_audit(c2.db, expected_balance=1000.0, expected_placed=0, expected_manual=0)

def test_crash_pre_click():
    print("=== PHASE 2: CRASH POST-PRE_COMMIT / PRE-CLICK (La Zona d'Ombra Inizia) ===")
    c = create_mock_controller()
    reset_ledger(c)
    
    c.worker.executor._chaos_hooks["crash_pre_click"] = True
    
    try: execute_signal(c, "Match 2")
    except RuntimeError: pass
    
    c2 = create_mock_controller()
    # Expect: PRE_COMMIT scritto. Bootloader lo trasforma in MANUAL_CHECK. Soldi NON rimborsati.
    strict_audit(c2.db, expected_balance=998.0, expected_placed=0, expected_manual=1)

def test_session_drop_mid_flight():
    print("=== PHASE 3: SESSION DROP (Sessione invalida al momento del click) ===")
    c = create_mock_controller()
    reset_ledger(c)
    
    c.worker.executor._chaos_hooks["session_drop"] = True
    
    try: execute_signal(c, "Match 3")
    except Exception: pass
    
    c2 = create_mock_controller()
    # Expect: Uguale a Phase 2. L'intento c'era, l'azione è fallita ma serve check manuale.
    strict_audit(c2.db, expected_balance=998.0, expected_placed=0, expected_manual=1)

def test_crash_post_click():
    print("=== PHASE 4: CRASH POST-CLICK (Panic Ledger Trigger) ===")
    c = create_mock_controller()
    reset_ledger(c)
    
    c.worker.executor._chaos_hooks["crash_post_click"] = True
    
    try: execute_signal(c, "Match 4")
    except RuntimeError: pass
    
    # Simuliamo riavvio: Bootloader deve leggere il .panic file
    c2 = create_mock_controller()
    # Expect: Il .panic impone PLACED. Saldo aggiornato dal bookmaker simulato.
    strict_audit(c2.db, expected_balance=998.0, expected_placed=1, expected_manual=0)

def run_all():
    print("\n" + "🔥" * 50)
    print("GOD MODE V2.1 — TRANSACTIONAL COORDINATOR CERTIFICATION")
    print("🔥" * 50 + "\n")
    
    test_crash_pre_precommit()
    test_crash_pre_click()
    test_session_drop_mid_flight()
    test_crash_post_click()

    print("============================================================")
    print("👑 GOD MODE V2.1 PASSED – 2PC & WRITE-AHEAD LEDGER CERTIFIED")
    print("============================================================\n")

if __name__ == "__main__":
    run_all()
