import sys
import os
import logging
import sqlite3

current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = current_dir
while not os.path.exists(os.path.join(project_root, "core")) and project_root != "/":
    project_root = os.path.dirname(project_root)
if project_root not in sys.path: sys.path.insert(0, project_root)

from core.controller import SuperAgentController

def create_mock_controller():
    c = SuperAgentController(logging.getLogger("GOD_MODE_V2"))
    if hasattr(c.engine, 'breaker'): c.engine.breaker.manual_reset()
    c.worker.executor._mock_logged_in = True
    c.engine.betting_enabled = True
    return c

def reset_ledger(c):
    c.db.conn.execute("DELETE FROM journal")
    c.db.conn.execute("UPDATE balance SET current_balance=1000.0")
    c.db.conn.commit()
    c.worker.executor._chaos_hooks.clear()

def strict_audit(db, exp_bal, exp_placed, exp_manual):
    balance, _ = db.get_balance()
    journal = [dict(r) for r in db.conn.execute("SELECT * FROM journal").fetchall()]
    placed = len([r for r in journal if r['status'] == 'PLACED'])
    manual = len([r for r in journal if r['status'] == 'MANUAL_CHECK'])
    print(f"[AUDIT] Bal: €{balance:.2f} | PLACED: {placed} | MANUAL: {manual}")
    assert balance == exp_bal and placed == exp_placed and manual == exp_manual
    print("🟢 CONSISTENT\n")

def run_cert():
    print("🔥 GOD MODE V2.1 — TRANSACTIONAL COORDINATOR CERTIFICATION\n")
    c = create_mock_controller()

    print("=== PHASE 1: CRASH PRE-PRE_COMMIT ===")
    reset_ledger(c)
    orig = c.db.mark_pre_commit
    c.db.mark_pre_commit = lambda *a: exec('raise(sqlite3.OperationalError("I/O"))')
    try: c.engine.process_signal({"teams": "M1", "stake": 2.0}, c.money_manager)
    except: pass
    c.db.mark_pre_commit = orig
    boot1 = create_mock_controller()
    boot1.db.recover_reserved()
    strict_audit(boot1.db, 1000.0, 0, 0)

    print("=== PHASE 2: CRASH IN ZONA D'OMBRA (PRE-CLICK) ===")
    reset_ledger(c)
    c.worker.executor._chaos_hooks["crash_pre_click"] = True
    try: c.engine.process_signal({"teams": "M2", "stake": 2.0}, c.money_manager)
    except: pass
    boot2 = create_mock_controller()
    boot2.db.recover_reserved()
    strict_audit(boot2.db, 998.0, 0, 1)

    print("=== PHASE 3: CRASH POST-CLICK (PANIC PATH) ===")
    reset_ledger(c)
    c.worker.executor._chaos_hooks["crash_post_click"] = True
    try: c.engine.process_signal({"teams": "M3", "stake": 2.0}, c.money_manager)
    except: pass
    boot3 = create_mock_controller()
    boot3.db.resolve_panics() # Risolve il file .panic
    boot3.db.recover_reserved()
    strict_audit(boot3.db, 998.0, 1, 0)

if __name__ == "__main__":
    run_cert()
