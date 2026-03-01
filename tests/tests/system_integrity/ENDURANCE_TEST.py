import os
import sys
import time
import threading
import traceback
import logging
import psutil
import sqlite3
import uuid

current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = current_dir
while not os.path.exists(os.path.join(project_root, "core")) and project_root != "/":
    project_root = os.path.dirname(project_root)
if project_root not in sys.path: sys.path.insert(0, project_root)

print("\n" + "🛡️" * 50)
print("ENDURANCE & ENVIRONMENT TEST — EXTREME SURVIVAL SIMULATION")
print("🛡️" * 50 + "\n")

FAILURES = []
def fail(code, reason):
    msg = f"❌ FAIL [{code}] → {reason}"
    print(msg)
    FAILURES.append(msg)

def ok(code, desc): print(f"🟢 OK [{code}] → {desc}")

TEST_DIR = "endurance_env"
os.makedirs(TEST_DIR, exist_ok=True)
import core.config_paths
core.config_paths.CONFIG_DIR = TEST_DIR
with open(os.path.join(TEST_DIR, "config.yaml"), "w") as f:
    f.write("betting:\n  allow_place: false\n")

original_sleep = time.sleep
time.sleep = lambda s: original_sleep(s) if s < 1 else None

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
c = SuperAgentController(logging.getLogger("ENDURANCE"))
c.start_listening()

try:
    # 🛡️ FIX ARCHITETTURALE: Aggiornato l'hook al nuovo metodo atomico
    orig_reserve = c.money_manager.get_stake_and_reserve
    
    def mock_disk_full(*args, **kwargs): 
        raise sqlite3.OperationalError("database or disk is full")
        
    c.money_manager.get_stake_and_reserve = mock_disk_full
    
    try:
        c.engine.process_signal({"teams": "DISK_FULL", "market": "1"}, c.money_manager)
        ok("DISK_FULL_SURVIVAL", "Errore 'Disco Pieno' intercettato. Il bot non è crashato.")
    except Exception as e: 
        fail("DISK_FULL_SURVIVAL", f"L'errore disco pieno ha ucciso il bot: {e}")
        
    c.money_manager.get_stake_and_reserve = orig_reserve
    
    # 🧹 FIX: Il disco pieno attiva il blocco fatale del Breaker persistente. Sblocchiamolo per i prossimi test.
    if hasattr(c.engine, 'breaker'):
        c.engine.breaker.manual_reset()
        
except Exception as e: fail("DISK_FULL_SURVIVAL", str(e))

try:
    orig_find_odds = c.worker.executor.find_odds
    def mock_cloudflare(*args): raise Exception("Timeout 30000ms exceeded. (Cloudflare Captcha block)")
    c.worker.executor.find_odds = mock_cloudflare
    try:
        c.engine.process_signal({"teams": "CLOUDFLARE_BAN", "market": "1"}, c.money_manager)
        ok("CLOUDFLARE_BAN", "Blocco antibot catturato. Il motore ha abortito la giocata.")
    except Exception as e: fail("CLOUDFLARE_BAN", f"Eccezione non gestita: {e}")
    c.worker.executor.find_odds = orig_find_odds
    
    # Pulizia breaker post-cloudflare
    if hasattr(c.engine, 'breaker'):
        c.engine.breaker.manual_reset()

except Exception as e: fail("CLOUDFLARE_BAN", str(e))

try:
    shutdown_flag = {"finished": False}
    
    # 🛡️ FIX: Simula una scommessa che richiede 1.5 secondi per essere piazzata
    orig_place = c.worker.executor.place_bet
    def slow_place(*args, **kwargs):
        original_sleep(1.5)
        shutdown_flag["finished"] = True
        return orig_place(*args, **kwargs)
    
    c.worker.executor.place_bet = slow_place
    
    # Avviamo il segnale in un thread per non bloccare il main thread
    t = threading.Thread(target=c.engine.process_signal, args=({"teams": "SLOW_MATCH", "market": "1", "is_active": True}, c.money_manager))
    t.start()
    
    # Diamo all'engine 0.5 secondi per iniziare a processare (acquisire il semaforo)
    original_sleep(0.5)
    
    # Ora chiediamo lo spegnimento morbido. 
    # DEVE attendere che il semaforo venga rilasciato da slow_place.
    c.stop_listening()
    t.join()
    
    if not shutdown_flag["finished"]: 
        fail("GRACEFUL_SHUTDOWN", "Il comando ha troncato la scommessa in volo!")
    else: 
        ok("GRACEFUL_SHUTDOWN", "Chiusura elegante OK. Scommessa protetta prima dello stop.")
        
    c.worker.executor.place_bet = orig_place
except Exception as e: 
    fail("GRACEFUL_SHUTDOWN", str(e))

try:
    process = psutil.Process(os.getpid())
    mem_start = process.memory_info().rss
    for _ in range(2000):
        c.engine.process_signal({"teams": None}, c.money_manager)
        c.engine.process_signal({"teams": "SPAM", "market": "UNKNOWN"}, c.money_manager)
    mem_end = process.memory_info().rss
    diff_mb = (mem_end - mem_start) / 1024 / 1024
    if diff_mb > 50: fail("MEMORY_LEAK", f"Spazzatura RAM: {diff_mb:.2f} MB! Rischio OOM.")
    else: ok("MEMORY_LEAK", f"Nessun Memory Leak. RAM pulita (+{diff_mb:.2f} MB su 4000 segnali).")
except Exception as e: fail("MEMORY_LEAK", str(e))

print("\n"+"="*60)
try:
    c.worker.stop()
    c.engine.bus.stop()
except:
    pass

if FAILURES:
    print("🔴 ENDURANCE TEST: FAGLIE AMBIENTALI RILEVATE\n")
    sys.exit(1)
else:
    print("🟢 ENDURANCE TEST SUPERATO CON SUCCESSO")
    sys.exit(0)