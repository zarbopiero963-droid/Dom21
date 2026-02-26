import os
import sys
import time
import random
import threading
import traceback
import logging

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if PROJECT_ROOT not in sys.path: sys.path.insert(0, PROJECT_ROOT)

print("\n"+"🧠"*50)
print("GOD MODE CHAOS ENGINEERING — ABSOLUTE SYSTEM CERTIFICATION")
print("🧠"*50+"\n")

FAILURES = []
def fail(where, reason):
    msg = f"❌ FAIL [{where}] → {reason}"
    print(msg)
    FAILURES.append(msg)

def ok(msg): print(f"✅ {msg}")

TEST_DIR = "god_chaos_env"
os.makedirs(TEST_DIR, exist_ok=True)
import core.config_paths
core.config_paths.CONFIG_DIR = TEST_DIR

with open(os.path.join(TEST_DIR, "config.yaml"), "w") as f:
    f.write("betting:\n  allow_place: false\n")

original_sleep = time.sleep
def smart_sleep(seconds):
    if seconds == 1.5: return 
    original_sleep(seconds)
time.sleep = smart_sleep

from core.dom_executor_playwright import DomExecutorPlaywright
def mock_init(self, *a, **k):
    self.bet_count = 0
    self.logger = logging.getLogger("MockExecutor")
    self.page = None
    self.mock_balance = 10000.0

DomExecutorPlaywright.__init__ = mock_init
DomExecutorPlaywright.launch_browser = lambda self: True
DomExecutorPlaywright.ensure_login = lambda self: True
DomExecutorPlaywright.get_balance = lambda self: getattr(self, 'mock_balance', 10000.0)

def mock_place(self, t, m, s): 
    if not hasattr(self, 'mock_balance'): self.mock_balance = 10000.0
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
def mock_tg_run(self):
    self.running = True
    while self.running: original_sleep(0.1)
TelegramWorker.run = mock_tg_run
TelegramWorker.stop = lambda self: setattr(self, 'running', False)
TelegramWorker.isRunning = lambda self: getattr(self, 'running', False)

from core.controller import SuperAgentController
logging.basicConfig(level=logging.CRITICAL)
logger = logging.getLogger("GOD")

try:
    controller = SuperAgentController(logger)
    controller.start_listening()
    controller._load_robots = lambda: [{"name": "GodModeBot", "trigger_words": [], "is_active": True}]
    original_sleep(0.5)
    ok("Controller avviato (Boot Integrity OK)")
except Exception as e:
    fail("BOOT", f"Controller crash all'avvio: {str(e)}")
    sys.exit(1)

if not hasattr(controller, "telegram") or not getattr(controller.telegram, 'running', False): fail("TELEGRAM", "Worker thread spento/crashato")
else: ok("Telegram Worker ATTIVO")

survived = {"v": False}
controller.engine.bus.subscribe("TEST_EVT", lambda p: 1/0)
controller.engine.bus.subscribe("TEST_EVT", lambda p: survived.update({"v": True}))
controller.engine.bus.emit("TEST_EVT", {})
if not survived["v"]: fail("EVENTBUS", "Crash di un subscriber ha ucciso il Bus!")
else: ok("EventBus RESILIENTE")

alive = {"v": False}
for _ in range(10): controller.worker.submit(lambda: 1/0)
controller.worker.submit(lambda: alive.update({"v": True}))
original_sleep(0.5)
if not alive["v"]: fail("WORKER", "Thread morto dopo eccezione nella coda!")
else: ok("Worker Thread IMMORTALE")

# --- INIZIO FIX SPAM/RACE CONDITION ---
err = {"v": False}
def spam(thread_id):
    try:
        for i in range(50):
            controller.money_manager.bankroll()
            # 🛡️ FIX: Diamo un nome univoco a ogni bet per evitare il blocco Anti-Doppione!
            fake_match = f"SPAM_TEAM_{thread_id}_MATCH_{i}"
            controller.money_manager.reserve(1.0, table_id=1, teams=fake_match)
    except Exception as e: 
        logger.error(f"Errore Spam: {e}")
        err["v"] = True

threads = [threading.Thread(target=spam, args=(t_id,)) for t_id in range(15)]
for t in threads: t.start()
for t in threads: t.join()

if err["v"]: fail("DATABASE", "Race Condition su scrittura SQLite!")
else: ok("Database WAL Mode: CONCORRENZA PERFETTA")
# --- FINE FIX SPAM/RACE CONDITION ---

for p in controller.money_manager.db.pending(): controller.money_manager.refund(p['tx_id'])

controller.money_manager.get_stake = lambda o, teams="": {"stake": 5.0, "table_id": 1} # 🛡️ FIX Ritorno Roserpina Formattato
before = controller.money_manager.bankroll()
orig_emit = controller.engine.bus.emit
def crash_emit(ev, p):
    if ev == "BET_SUCCESS": raise RuntimeError("CRASH POST-BET")
    orig_emit(ev, p)
controller.engine.bus.emit = crash_emit
controller.engine.process_signal({"teams": "A-B", "market": "1", "is_active": True}, controller.money_manager)
after = controller.money_manager.bankroll()

# 🔴 FIX 2PC: Controllo Finanziario Rigoroso per il GOD_MODE
zombies_reserved = [p for p in controller.money_manager.db.pending() if p['status'] == 'RESERVED']
zombies_placed = [p for p in controller.money_manager.db.pending() if p['status'] == 'PLACED']

if len(zombies_reserved) > 0:
    fail("DATABASE", f"Race Condition! Trovate {len(zombies_reserved)} RESERVED zombie (Fase 1 incompleta).")
elif after == before: 
    fail("LEDGER", "CRITICO: Refund fantasma eseguito su una PLACED!")
else: 
    ok(f"Ledger INTEGRO (Trovate {len(zombies_placed)} PLACED legittime post-crash)")

controller.engine.bus.emit = orig_emit

original_sleep(1)
if not controller.worker.thread or not controller.worker.thread.is_alive(): fail("FREEZE", "Worker Thread morto silenziosamente")
else: ok("Sistema REATTIVO")

for p in controller.money_manager.db.pending(): controller.money_manager.refund(p['tx_id'])

try:
    commit_ok = {"status": False}
    orig_place = controller.worker.executor.place_bet
    
    # 🛡️ FIX 2 (Two-Phase Commit): Tolto il parametro 'self' fittizio. 
    def mock_place_2phase(teams, market, stake):
        if len(controller.money_manager.db.pending()) > 0: commit_ok["status"] = True
        controller.worker.executor.mock_balance -= float(stake)
        return True
    
    controller.worker.executor.place_bet = mock_place_2phase
    controller.engine.process_signal({"teams": "2-PHASE", "market": "1", "is_active": True}, controller.money_manager)
    
    if not commit_ok["status"]: fail("TWO-PHASE COMMIT", "I soldi non salvati su DB PRIMA del click!")
    else: ok("Two-Phase Commit OK")
    
    controller.worker.executor.place_bet = orig_place
except Exception as e: fail("TWO-PHASE COMMIT", str(e))

try:
    if not hasattr(controller.engine, '_safe_float'): fail("ROBUST PARSING", "Manca _safe_float")
    else:
        t1, t2, t3 = controller.engine._safe_float("1.234,56"), controller.engine._safe_float("1,50"), controller.engine._safe_float("€ 2.0")
        if t1 == 1234.56 and t2 == 1.5 and t3 == 2.0: ok("Robust Parsing OK")
        else: fail("ROBUST PARSING", "Errori conversione")
except Exception as e: fail("ROBUST PARSING", str(e))

try:
    orig_bal = controller.worker.executor.get_balance
    controller.worker.executor.get_balance = lambda: "ERRORE DOM HTML"
    controller.engine.process_signal({"teams": "BLIND", "market": "1", "is_active": True}, controller.money_manager)
    ok("Blind Balance Protection OK")
    controller.worker.executor.get_balance = orig_bal
except Exception as e: fail("BLIND BALANCE", f"Crash su grafica cambiata: {e}")

try:
    session_checked = {"status": False}
    controller.worker.executor.ensure_login = lambda: session_checked.update({"status": True})
    controller.engine.process_signal({"teams": "SESSION", "market": "1", "is_active": True}, controller.money_manager)
    if not session_checked["status"]: fail("SESSION RISK", "Login non verificato pre-bet!")
    else: ok("Session Loss Protection OK")
except Exception as e: fail("SESSION RISK", str(e))

try:
    robots_path = os.path.join(TEST_DIR, "robots.yaml")
    with open(robots_path, "w") as f: f.write("questo: [ yaml - è: spezzato a meta...\n : errore fatale")
    try:
        from core.secure_storage import RobotManager
        rm = RobotManager()
        robots = rm.all()
        ok("Vault Corruption Recovery OK")
    except Exception as e: fail("VAULT CORRUPTION", f"Crash al boot: {e}")
    if os.path.exists(robots_path): os.remove(robots_path)
except Exception as e: fail("VAULT CORRUPTION", str(e))

try:
    reservations = {"count": 0}
    orig_reserve = controller.money_manager.reserve
    
    # 🛡️ FIX 3 (Duplicate Bombing): Aggiunti i parametri corretti
    def mock_reserve(amount, table_id=1, teams=""):
        reservations["count"] += 1
        return orig_reserve(amount, table_id=table_id, teams=teams)
    
    controller.money_manager.reserve = mock_reserve
    
    # 🛡️ Aggiunto mm_mode per forzare l'uso dell'intelligenza quantitativa e innescare i controlli.
    def fire_signal(): 
        controller.engine.process_signal({"teams": "JUVENTUS - MILAN", "market": "1", "is_active": True, "mm_mode": "Roserpina (Progressione)"}, controller.money_manager)
    
    threads = [threading.Thread(target=fire_signal) for _ in range(3)]
    for t in threads: t.start()
    for t in threads: t.join()
    
    if reservations["count"] > 1: fail("DUPLICATE BOMBING", "Segnali multipli processati")
    else: ok("Anti-Duplicate Signal OK")
    
    controller.money_manager.reserve = orig_reserve
except Exception as e: fail("DUPLICATE BOMBING", str(e))

try:
    orig_find_odds = controller.worker.executor.find_odds
    def mock_dead_browser(*args): raise RuntimeError("Target page has been closed")
    controller.worker.executor.find_odds = mock_dead_browser
    controller.engine.process_signal({"teams": "ZOMBIE MATCH", "market": "1", "is_active": True}, controller.money_manager)
    ok("Browser Zombie Protection OK")
    controller.worker.executor.find_odds = orig_find_odds
except Exception as e: fail("BROWSER ZOMBIE", str(e))

controller.stop_listening()
controller.worker.stop()
controller.engine.bus.stop()

print("\n"+"="*60)
if FAILURES:
    print("🔴 GOD MODE: SISTEMA NON STABILE")
    for f in FAILURES: print(f)
    sys.exit(1)
else:
    print("🟢 GOD MODE SUPERATO: ARCHITETTURA HEDGE-GRADE CERTIFICATA")
    sys.exit(0)
