import os
import sys
import time
import threading
import logging
import math

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
core.config_paths.CONFIG_DIR = TEST_DIR

with open(os.path.join(TEST_DIR, "config.yaml"), "w") as f:
    f.write("betting:\n  allow_place: false\n")

original_sleep = time.sleep
time.sleep = lambda s: original_sleep(s) if s < 1 else None

def create_mocked_controller():
    from core.dom_executor_playwright import DomExecutorPlaywright

    def mock_init(self, *a, **k):
        self.bet_count = 0
        self.logger = logging.getLogger("MockExecutor")
        self.page = None
        self.mock_balance = 1000.0 

    DomExecutorPlaywright.__init__ = mock_init
    DomExecutorPlaywright.launch_browser = lambda self: True
    DomExecutorPlaywright.ensure_login = lambda self: True
    DomExecutorPlaywright.get_balance = lambda self: getattr(self, 'mock_balance', 1000.0) 
    
    def mock_place(self, t, m, s): 
        if not hasattr(self, 'mock_balance'): self.mock_balance = 1000.0
        self.mock_balance -= float(s) 
        return True
        
    DomExecutorPlaywright.place_bet = mock_place
    # 👇 FIX: Aggiunto is_live=True
    DomExecutorPlaywright.navigate_to_match = lambda self, t, is_live=True: True
    
    DomExecutorPlaywright.find_odds = lambda self, t, m: 2.0
    DomExecutorPlaywright.check_settled_bets = lambda self: None
    DomExecutorPlaywright.check_open_bet = lambda self: False
    DomExecutorPlaywright.save_blackbox = lambda self, *args, **kwargs: None

    from core.telegram_worker import TelegramWorker
    TelegramWorker.run = lambda self: None
    TelegramWorker.stop = lambda self: None

    from core.controller import SuperAgentController
    logging.basicConfig(level=logging.CRITICAL)
    return SuperAgentController(logging.getLogger("ULTRA"))

# TEST 1
try:
    c1 = create_mocked_controller()
    def hard_kill_mock(*args): raise SystemExit("OS KILL PROCESS")
    c1.worker.executor.place_bet = hard_kill_mock
    try: c1.engine.process_signal({"teams": "REBOOT_TEST", "market": "1"}, c1.money_manager)
    except SystemExit: pass
    c2 = create_mocked_controller()
    pending = c2.money_manager.db.pending()
    if len(pending) == 0: fail("DOUBLE_BET_REBOOT", "Bet non registrata.", "execution_engine.py", "Doppia bet.")
    else:
        ok("DOUBLE_BET_REBOOT", "2-phase commit corretto.")
        for p in pending: c2.money_manager.refund(p['tx_id'])
except Exception as e: fail("DOUBLE_BET_REBOOT", str(e), "engine", "Unknown")

# TEST 2
try:
    c = create_mocked_controller()
    def slow(payload): original_sleep(2)
    c.engine.bus.subscribe("BLOCK", slow)
    start = time.time()
    c.engine.bus.emit("BLOCK", {})
    if time.time() - start > 1: fail("EVENT_BUS_BLOCK", "Bus bloccato", "event_bus.py", "Freeze engine.")
    else: ok("EVENT_BUS_BLOCK", "Bus non blocca engine")
except Exception as e: fail("EVENT_BUS_BLOCK", str(e), "bus", "Unknown")

# TEST 3
try:
    c = create_mocked_controller()
    import core.money_management
    has_watchdog = hasattr(c.money_manager, "reconcile_balances") or hasattr(core.money_management.MoneyManager, "reconcile_balances")
    if not has_watchdog: fail("MISSING_FIN_WATCHDOG", "Watchdog assente", "money_management.py", "Mismatch.")
    else: ok("MISSING_FIN_WATCHDOG", "Watchdog integrato")
except Exception as e: fail("MISSING_FIN_WATCHDOG", str(e), "mm", "Unknown")

# TEST 4
try:
    c = create_mocked_controller()
    c.money_manager.db.update_bankroll(100.0)
    def spam():
        try:
            stake = c.money_manager.get_stake(2.0)
            if stake > 0: c.money_manager.reserve(stake)
        except: pass
    threads = [threading.Thread(target=spam) for _ in range(50)]
    for t in threads: t.start()
    for t in threads: t.join()
    pending_sum = sum([p['amount'] for p in c.money_manager.db.pending()])
    if pending_sum > 100: fail("OVER_RESERVE", f"Reserved {pending_sum}€ su 100€", "mm", "Bancarotta")
    else: ok("OVER_RESERVE", f"Bankroll protetto. Pending: {pending_sum}€")
    for p in c.money_manager.db.pending(): c.money_manager.refund(p['tx_id'])
except Exception as e: fail("OVER_RESERVE", str(e), "mm", "Unknown")

# TEST 5
try:
    c = create_mocked_controller()
    poisoned = False
    for s in [float("inf"), float("-inf"), float("nan"), -50.0, 0.0]:
        try:
            tx = c.money_manager.reserve(s)
            val = c.money_manager.db.get_transaction(tx)['amount']
            if math.isnan(val) or val <= 0: poisoned = True
        except: pass
    if poisoned: fail("MATH_POISON", "Stake illegali", "mm", "DB corrotto")
    else: ok("MATH_POISON", "Sanity check stake OK")
except Exception as e: fail("MATH_POISON", str(e), "mm", "Unknown")

# TEST 6
try:
    c = create_mocked_controller()
    for p in c.money_manager.db.pending(): c.money_manager.refund(p['tx_id'])
    def drop(*args): raise ConnectionError("internet down")
    c.worker.executor.place_bet = drop
    c.engine.process_signal({"teams": "ZOMBIE", "market": "1"}, c.money_manager)
    zombies = [p for p in c.money_manager.db.pending() if p['status'] == "PENDING"]
    if len(zombies) > 0: fail("ZOMBIE_TX", "Pending rimasto", "engine", "Blocco fondi")
    else: ok("ZOMBIE_TX", "Rollback corretto contro crash")
except Exception as e: fail("ZOMBIE_TX", str(e), "engine", "Unknown")

# TEST 7
try:
    c = create_mocked_controller()
    c._load_robots = lambda: [{"name": "TestBot", "trigger_words": ["calcio"], "is_active": False}]
    c.is_running = False
    c.engine.betting_enabled = False
    res_off = c.process_signal({"teams": "Roma", "market": "1", "raw_text": "calcio roma"})
    
    c.is_running = True
    c.engine.betting_enabled = True
    res_robot_off = c.process_signal({"teams": "Roma", "market": "1", "raw_text": "calcio roma"})

    if res_off is not False: fail("CIRCUIT_BREAKER_FAIL", "Processato a motore OFF", "controller.py", "Perdita fondi")
    elif res_robot_off is not False: fail("ZOMBIE_ROBOT_FAIL", "Processato a robot in pausa", "controller.py", "Strategie zombie")
    else: ok("COMMAND_CENTER_LOCKS", "Circuit Breakers verificati.")
except Exception as e: fail("COMMAND_CENTER_LOCKS", str(e), "controller.py", "Unknown")

print("\n" + "=" * 60)
if FAILURES:
    print("🔴 ULTRA SYSTEM TEST: ERRORI CRITICI")
    sys.exit(1)
else:
    print("🟢 ULTRA SYSTEM TEST SUPERATO CON SUCCESSO")
    sys.exit(0)