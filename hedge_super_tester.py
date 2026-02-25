import os
import sys
import time
import threading
import traceback
import logging
import psutil
import signal

print("\n" + "="*60)
print("🧠 DOM2 HEDGE FUND STABILITY TEST (V8.5)")
print("="*60)

TEST_DIR = os.path.join(os.getcwd(), "ci_test_env")
os.makedirs(TEST_DIR, exist_ok=True)

import core.config_paths
core.config_paths.CONFIG_DIR = TEST_DIR

from core.dom_executor_playwright import DomExecutorPlaywright

def mocked_launch_browser(self): return True
DomExecutorPlaywright.launch_browser = mocked_launch_browser

def mocked_ensure_login(self): return True
DomExecutorPlaywright.ensure_login = mocked_ensure_login

# 👇 FIX: Aggiunto is_live=True
def mocked_navigate(self, teams, is_live=True): return True
DomExecutorPlaywright.navigate_to_match = mocked_navigate

def mocked_odds(self, teams, market): return 1.50
DomExecutorPlaywright.find_odds = mocked_odds

def mocked_get_balance(self):
    if not hasattr(self, 'mock_balance'): self.mock_balance = 1000.0
    return self.mock_balance
DomExecutorPlaywright.get_balance = mocked_get_balance

def mocked_place(self, teams, market, stake):
    print(f"🔧 HEDGE MOCK: Scommessa piazzata simulata ({stake}€)")
    time.sleep(1)
    if not hasattr(self, 'mock_balance'): self.mock_balance = 1000.0
    self.mock_balance -= float(stake)
    return True
DomExecutorPlaywright.place_bet = mocked_place

def mocked_check_open(self): return False
DomExecutorPlaywright.check_open_bet = mocked_check_open

def mocked_check_settled(self): return None
DomExecutorPlaywright.check_settled_bets = mocked_check_settled

try:
    from core.controller import SuperAgentController
    from core.event_bus import bus
    from core.events import AppEvent
except ImportError as e:
    print(f"❌ CRITICAL IMPORT ERROR: {e}")
    sys.exit(1)

logging.basicConfig(level=logging.INFO, format="%(asctime)s | HEDGE | %(message)s")
logger = logging.getLogger("HEDGE")

crash_flag = {"dead": False}
def global_excepthook(exctype, value, tb):
    print("\n🔥 GLOBAL PYTHON CRASH RILEVATO")
    traceback.print_exception(exctype, value, tb)
    crash_flag["dead"] = True
sys.excepthook = global_excepthook

if hasattr(signal, "SIGALRM"):
    signal.signal(signal.SIGALRM, lambda s, f: sys.exit(1))
    signal.alarm(180)

try:
    print("🚀 Avvio Controller...")
    controller = SuperAgentController(logger)
    controller.start_listening()
    controller._load_robots = lambda: [{"name": "HedgeTestBot", "trigger_words": [], "is_active": True}]
    print("✅ Controller avviato.")
except Exception as e:
    print(f"❌ CRASH ALL'AVVIO: {e}")
    sys.exit(1)

time.sleep(2)
if not controller.worker.thread or not controller.worker.thread.is_alive():
    print("❌ CRITICAL: Worker Thread morto!")
    sys.exit(1)

result = {"status": "WAITING"}
def on_success(payload):
    result["status"] = "WIN"
    print(f"🏆 EVENT SUCCESS: {payload}")
def on_fail(payload):
    result["status"] = "FAIL_HANDLED"
    print(f"🛡️ FAIL GESTITO (Expected): {payload.get('reason')}")

bus.subscribe(AppEvent.BET_SUCCESS, on_success)
bus.subscribe(AppEvent.BET_FAILED, on_fail)

fake_signal = {"teams": "HEDGE TEST", "market": "WINNER", "raw_text": "hedge test live"}
print("💉 INIEZIONE SEGNALE TEST...")
controller.handle_signal(fake_signal)

start_time = time.time()
while time.time() - start_time < 60:
    if result["status"] == "WIN": break
    if crash_flag["dead"]: sys.exit(1)
    if not controller.worker.thread or not controller.worker.thread.is_alive(): sys.exit(1)
    time.sleep(1)

print("\n🔍 AUDIT SISTEMA...")
try:
    rows = controller.db.conn.execute("SELECT * FROM journal").fetchall()
    print(f"📊 DB Journal Entries: {len(rows)}")
    if len(rows) == 0: sys.exit(1)
except Exception as e: sys.exit(1)

controller.stop_listening()
controller.worker.stop()
bus.stop()

if result["status"] == "WAITING":
    print("\n❌ TIMEOUT")
    sys.exit(1)

print("\n" + "="*60)
print(f"🟢 HEDGE TEST PASSATO: Sistema Stabile. Esito: {result['status']}")
print("="*60)
sys.exit(0)