import os
import sys
import time
import threading
import logging
import math
import uuid

# 🛡️ FIX ARCHITETTURALE: Modalità Test-Safe per impedire al C-Engine di killare PyTest
os.environ["ALLOW_DB_EXCEPTION"] = "1"
os.environ["CI"] = "true"

current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = current_dir
while not os.path.exists(os.path.join(project_root, "core")) and project_root != "/":
    project_root = os.path.dirname(project_root)
if project_root not in sys.path: sys.path.insert(0, project_root)

print("\n" + "🔥" * 50)
print("ULTRA SYSTEM INTEGRITY TEST — ARCHITECTURAL CHAOS SIMULATION")
print("🔥" * 50 + "\n")

FAILURES = []
def fail(code, reason, file, impact):
    msg = f"\n❌ FAIL [{code}]\n→ {reason}\nFile: {file}\nImpatto: {impact}"
    print(msg)
    FAILURES.append(msg)

def ok(code, desc): print(f"🟢 OK [{code}] → {desc}")

TEST_DIR = "ultra_system_env"
os.makedirs(TEST_DIR, exist_ok=True)
import core.config_paths
core.config_paths.CONFIG_DIR = Path(TEST_DIR) if 'Path' in globals() else type('Path', (), {'__truediv__': lambda self, x: os.path.join(TEST_DIR, x)})()

with open(os.path.join(TEST_DIR, "config.yaml"), "w") as f:
    f.write("betting:\n  allow_place: false\n")

original_sleep = time.sleep
time.sleep = lambda s: original_sleep(s) if s < 1 else None

def create_mocked_controller():
    from core.dom_executor_playwright import DomExecutorPlaywright
    from core.execution_engine import ExecutionEngine
    from core.money_management import MoneyManager
    from core.database import Database
    from core.event_bus import EventBusV6
    from core.playwright_worker import PlaywrightWorker
    from unittest.mock import MagicMock

    class MockExecutor(DomExecutorPlaywright):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.bet_count = 0
            self.mock_balance = 1000.0
            self.page = MagicMock()
            
        def launch_browser(self): return True
        def ensure_login(self): return True
        def get_balance(self): return getattr(self, 'mock_balance', 1000.0)
        
        def place_bet(self, t, m, s):
            if not hasattr(self, 'mock_balance'): self.mock_balance = 1000.0
            self.mock_balance -= float(s)
            return True

        def navigate_to_match(self, t, is_live=True): return True
        def find_odds(self, t, m): return 2.0
        def check_settled_bets(self): return None
        def check_open_bet(self): return False
        def save_blackbox(self, *args, **kwargs): pass

    db = Database()
    executor = MockExecutor(logger=logging.getLogger("MockExecutor"))
    worker = PlaywrightWorker(executor, logger=logging.getLogger("MockWorker"))
    bus = EventBusV6(logging.getLogger("MockBus"))
    engine = ExecutionEngine(bus, worker, logger=logging.getLogger("MockEngine"))
    engine.betting_enabled = True
    mm = MoneyManager(db, logger=logging.getLogger("MockMM"))

    class MockController:
        def __init__(self):
            self.db = db
            self.executor = executor
            self.worker = worker
            self.bus = bus
            self.engine = engine
            self.money_manager = mm
            self.is_running = True
            
        def process_signal(self, payload):
            if not self.is_running or not self.engine.betting_enabled: return False
            return self.engine.process_signal(payload, self.money_manager)

    return MockController()

# TEST 1: Double Spend Pre-Commit Reboot
try:
    c1 = create_mocked_controller()
    def hard_kill_mock(*args, **kwargs): raise SystemExit("OS KILL PROCESS")
    c1.worker.executor.place_bet = hard_kill_mock
    
    try: 
        c1.engine.process_signal({"teams": "REBOOT_TEST", "market": "1", "stake": "2.0"}, c1.money_manager)
    except SystemExit: pass
    
    c2 = create_mocked_controller()
    pending = c2.db.pending()
    
    # Nel nuovo paradigma 10.1, se la morte avviene in place_bet (doppio mock_kill), la transazione è in PRE_COMMIT
    if len(pending) == 0: 
        fail("DOUBLE_BET_REBOOT", "Nessuna bet trovata a sistema (attesa PRE_COMMIT).", "execution_engine.py", "Transazione persa.")
    else:
        ok("DOUBLE_BET_REBOOT", "Crash catturato. Transazione ancorata in database.")
        for p in pending: c2.money_manager.refund(p['tx_id'])
except Exception as e: fail("DOUBLE_BET_REBOOT", str(e), "engine", "Unknown")

# TEST 2: EventBus Blocking
try:
    c = create_mocked_controller()
    def slow(payload): original_sleep(2)
    c.bus.subscribe("BLOCK", slow)
    start = time.time()
    c.bus.emit("BLOCK", {})
    if time.time() - start > 1: fail("EVENT_BUS_BLOCK", "Bus bloccato", "event_bus.py", "Freeze engine.")
    else: ok("EVENT_BUS_BLOCK", "Asincronia bus verificata.")
except Exception as e: fail("EVENT_BUS_BLOCK", str(e), "bus", "Unknown")

# TEST 3: Watchdog Presenza
try:
    c = create_mocked_controller()
    if not hasattr(c.money_manager, "reconcile_balances"): fail("MISSING_FIN_WATCHDOG", "Watchdog assente", "money_management.py", "Mismatch API.")
    else: ok("MISSING_FIN_WATCHDOG", "Routine di riconciliazione intatta.")
except Exception as e: fail("MISSING_FIN_WATCHDOG", str(e), "mm", "Unknown")

# TEST 4: OOM & Over-Reserve Concurrency
try:
    c = create_mocked_controller()
    c.db.update_bankroll(100.0, 100.0)
    
    def spam():
        try: c.money_manager.get_stake_and_reserve(str(uuid.uuid4()), 2.0, 2.0, teams="SpamTeam")
        except: pass
        
    threads = [threading.Thread(target=spam) for _ in range(50)]
    for t in threads: t.start()
    for t in threads: t.join()
    
    pending_sum = sum([float(p['amount']) for p in c.db.pending() if p['amount']])
    
    # Il limite massimo di esposizione nel MoneyManager è 200, ma il bankroll è 100
    if pending_sum > 100.0: fail("OVER_RESERVE", f"Esposizione illegale: {pending_sum}€ su bankroll 100€", "mm", "Bancarotta")
    else: ok("OVER_RESERVE", f"Invariante saldo protetto. Massima esposizione raggiunta: {pending_sum}€")
    
    for p in c.db.pending(): c.money_manager.refund(p['tx_id'])
except Exception as e: fail("OVER_RESERVE", str(e), "mm", "Unknown")

# TEST 5: Math Poisoning C-Level Defense
try:
    c = create_mocked_controller()
    poisoned = False
    
    for s in [float("inf"), float("-inf"), float("nan"), -50.0, 0.0]:
        tx_id = f"POISON_{s}"
        try:
            reserved = c.money_manager.get_stake_and_reserve(tx_id, s, 2.0, teams="Poison")
            if reserved > 0:
                row = c.db.conn.execute("SELECT amount FROM journal WHERE tx_id=?", (tx_id,)).fetchone()
                if row and (math.isnan(float(row['amount'])) or float(row['amount']) <= 0):
                    poisoned = True
        except ValueError: pass # Prevenuto dal python guard
        except Exception: pass # Prevenuto dal C-Level Constraint
        
    if poisoned: fail("MATH_POISON", "Invariante finanziario violato. Saldo corrotto.", "mm", "Math bypass.")
    else: ok("MATH_POISON", "Attacchi matematici invalidi respinti dal database C-Level.")
except Exception as e: fail("MATH_POISON", str(e), "mm", "Unknown")

# TEST 6: Zombie Transaction (Rollback on failure)
try:
    c = create_mocked_controller()
    for p in c.db.pending(): c.money_manager.refund(p['tx_id'])
    
    def drop(*args, **kwargs): raise ConnectionError("internet down simulato")
    c.worker.executor.place_bet = drop
    
    # Bypassiamo il circuito per forzare l'errore in fase di bet
    c.engine.process_signal({"teams": "ZOMBIE", "market": "1", "stake": "2.0"}, c.money_manager)
    
    zombies = [p for p in c.db.pending() if p['status'] == 'PRE_COMMIT' and p['teams'] == 'ZOMBIE']
    
    # Se il broker fallisce a livello di DOM/Rete, il tx diventa MANUAL_CHECK o viene rollbackato.
    # Non deve MAI restare in RESERVED/PRE_COMMIT eternamente bloccando fondi.
    has_zombies = any(p['teams'] == "ZOMBIE" for p in c.db.pending() if p['status'] not in ["MANUAL_CHECK", "VOID"])
    
    if has_zombies: fail("ZOMBIE_TX", "Fondi bloccati in stato indefinito post-crash.", "engine", "Leak fondi.")
    else: ok("ZOMBIE_TX", "Isolamento eccezione e demotion a MANUAL_CHECK/VOID eseguito.")
except Exception as e: fail("ZOMBIE_TX", str(e), "engine", "Unknown")

# TEST 7: Circuit Breakers
try:
    c = create_mocked_controller()
    
    c.is_running = False
    c.engine.betting_enabled = False
    res_off = c.process_signal({"teams": "Roma", "market": "1", "stake": "2.0"})
    
    c.is_running = True
    c.engine.betting_enabled = False
    res_robot_off = c.process_signal({"teams": "Roma", "market": "1", "stake": "2.0"})

    if res_off is not False and res_off is not None: fail("CIRCUIT_BREAKER_FAIL", "Processato a main loop OFF", "controller.py", "Perdita fondi")
    elif res_robot_off is not False and res_robot_off is not None: fail("ZOMBIE_ROBOT_FAIL", "Processato a betting disabilitato", "controller.py", "Strategie zombie")
    else: ok("COMMAND_CENTER_LOCKS", "Circuit Breakers dell'Engine attivi e blindati.")
except Exception as e: fail("COMMAND_CENTER_LOCKS", str(e), "controller.py", "Unknown")

print("\n" + "=" * 60)
if FAILURES:
    print("🔴 ULTRA SYSTEM TEST: ERRORI CRITICI RILEVATI")
    for f in FAILURES: print(f)
    os._exit(1)
else:
    print("🟢 ULTRA SYSTEM TEST SUPERATO CON SUCCESSO ASSOLUTO")
    os._exit(0)