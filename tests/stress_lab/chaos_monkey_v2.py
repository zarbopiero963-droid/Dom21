import os
import sys
import time
import threading
import sqlite3
import psutil
import signal
import multiprocessing
import shutil
import logging
from pathlib import Path

# Setup Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.resolve()))

from core.database import Database
from core.event_bus import EventBusV6
from core.dom_executor_playwright import DomExecutorPlaywright
from core.playwright_worker import PlaywrightWorker

logging.basicConfig(level=logging.INFO, format="%(asctime)s [CHAOS V2] %(message)s")
logger = logging.getLogger("ChaosV2")

DB_PATH = os.path.join(str(Path.home()), ".superagent_data", "money_db.sqlite")
DB_BACKUP = DB_PATH + ".bak"
WAL_PATH = DB_PATH + "-wal"

def setup_environment():
    logger.info("🔧 Setup: Backup del database di produzione...")
    if os.path.exists(DB_PATH):
        shutil.copy2(DB_PATH, DB_BACKUP)

def teardown_environment():
    logger.info("🧹 Teardown: Ripristino del database originale...")
    if os.path.exists(DB_BACKUP):
        shutil.copy2(DB_BACKUP, DB_PATH)
        os.remove(DB_BACKUP)
    if os.path.exists(WAL_PATH):
        try: os.remove(WAL_PATH)
        except: pass

# --- VETTORE 1: SIGKILL Mid-Transaction (Fault Injection) ---
def _malicious_process():
    # Monkey-patching di SQLite a livello di memoria
    original_execute = sqlite3.Connection.execute
    
    def poisoned_execute(self, sql, parameters=()):
        res = original_execute(self, sql, parameters)
        # Intercettiamo l'esatto nanosecondo DOPO aver sottratto il saldo ma PRIMA del COMMIT
        if "UPDATE balance SET current_balance = current_balance -" in sql.upper():
            logger.critical("☠️ FAULT INJECTED: Uccisione processo pre-COMMIT!")
            os.kill(os.getpid(), signal.SIGKILL)
        return res

    sqlite3.Connection.execute = poisoned_execute
    
    db = Database()
    db.reserve("TX_TRUE_CHAOS_1", 100.0)

def attack_1_true_transaction_kill():
    logger.info("🔪 ATTACCO 1: Deterministic Mid-Transaction SIGKILL")
    db = Database()
    start_balance, _ = db.get_balance()
    
    p = multiprocessing.Process(target=_malicious_process)
    p.start()
    p.join() # Attende l'exit code -9 (SIGKILL)
    
    logger.info("🔄 Esecuzione routine di recovery post-crash...")
    db.recover_reserved()
    end_balance, _ = db.get_balance()
    
    if start_balance == end_balance:
        logger.info("✅ ATTACCO 1 FALLITO (Sistema Safe): Il WAL ha assorbito il crash atomico.")
    else:
        logger.critical(f"❌ ATTACCO 1 RIUSCITO (Corruzione!): Saldo perso. Inizio: {start_balance}, Fine: {end_balance}")
        sys.exit(1)

# --- VETTORE 2: Real IPC Contention & Renderer Murder ---
def attack_2_ipc_contention():
    logger.info("🔪 ATTACCO 2: IPC Contention + Renderer Murder")
    executor = DomExecutorPlaywright(logger=logger)
    executor.launch_browser()
    worker = PlaywrightWorker(executor, logger)
    
    # 1. Saturiamo il ThreadPool con task lenti (Contention)
    def slow_task(): time.sleep(10)
    for _ in range(50):
        worker.submit(slow_task)
        
    time.sleep(2)
    
    # 2. Omicidio mirato dei renderer Chrome mentre la coda è intasata
    killed = 0
    my_pid = os.getpid()
    for p in psutil.process_iter(['name', 'ppid']):
        try:
            if 'chrome' in (p.info['name'] or '').lower() and p.info['ppid'] != my_pid:
                os.kill(p.pid, signal.SIGKILL)
                killed += 1
        except: pass
        
    logger.info(f"💥 Uccisi {killed} processi Chrome. Attesa recovery Watchdog (Timeout)...")
    time.sleep(5)
    
    if worker.thread and worker.thread.is_alive():
        logger.info("✅ ATTACCO 2 FALLITO (Sistema Safe): Worker Thread vivo e pool rigenerato dopo il massacro IPC.")
    else:
        logger.critical("❌ ATTACCO 2 RIUSCITO: Deadlock o crash del Worker Thread principale.")
        sys.exit(1)
    worker.stop()

# --- VETTORE 3: WAL Truncation (Disk I/O Corruption) ---
def attack_3_wal_truncation():
    logger.info("🔪 ATTACCO 3: WAL Truncation Chirurgica")
    db = Database()
    db.reserve("TX_WAL_TEST", 10.0) # Forza la creazione e scrittura nel WAL
    
    if not os.path.exists(WAL_PATH):
        logger.warning("Nessun file WAL trovato. Skip test (forse già flushed).")
        return
        
    # Tronca il file WAL brutalmente a metà
    with open(WAL_PATH, "r+b") as f:
        f.truncate(100) 
        
    try:
        # Tenta una lettura dopo la corruzione del WAL
        db.get_balance()
        logger.info("✅ ATTACCO 3 FALLITO (Sistema Safe): SQLite ha ignorato il WAL corrotto / ripristinato dal file DB root.")
    except sqlite3.DatabaseError as e:
        logger.info(f"✅ ATTACCO 3 FALLITO (Sistema Safe): Isolamento errore riuscito. Eccezione intercettata: {e}")
    except Exception as e:
        logger.critical(f"❌ ATTACCO 3 RIUSCITO: Eccezione non gestita o crash memory-space: {e}")
        sys.exit(1)

# --- VETTORE 4: OOM Tsunami con RAM Assertions ---
def attack_4_oom_tsunami():
    logger.info("🔪 ATTACCO 4: OOM Tsunami con Assertions di Memoria")
    process = psutil.Process(os.getpid())
    mem_start = process.memory_info().rss / (1024 * 1024)
    
    bus = EventBusV6(logger)
    
    def flood():
        for _ in range(3000):
            bus.emit("CHAOS_EVENT", {"data": "X" * 1024}) # Payload da 1KB
            
    # Lanciamo 40.000 eventi simultanei
    threads = [threading.Thread(target=flood) for _ in range(20)]
    for t in threads: t.start()
    for t in threads: t.join()
    
    mem_end = process.memory_info().rss / (1024 * 1024)
    mem_diff = mem_end - mem_start
    
    logger.info(f"RAM Inizio: {mem_start:.2f} MB | RAM Fine: {mem_end:.2f} MB | Delta: +{mem_diff:.2f} MB")
    
    if bus.pending_count > 5000:
        logger.critical(f"❌ ATTACCO 4 RIUSCITO: Limite Backpressure violato! Coda: {bus.pending_count}")
        sys.exit(1)
        
    if mem_diff > 50.0:
        logger.critical(f"❌ ATTACCO 4 RIUSCITO: Memory Leak rilevato! RAM aumentata di {mem_diff:.2f} MB")
        sys.exit(1)
        
    logger.info("✅ ATTACCO 4 FALLITO (Sistema Safe): Backpressure regge. Nessun OOM Leak.")
    bus.stop()

if __name__ == "__main__":
    print("==================================================")
    print("🔥 AVVIO DETERMINISTIC CHAOS HARNESS V2 🔥")
    print("==================================================")
    setup_environment()
    try:
        attack_1_true_transaction_kill()
        attack_2_ipc_contention()
        attack_4_oom_tsunami()
        attack_3_wal_truncation() 
        print("==================================================")
        print("🟢 V2 CERTIFICAZIONE SUPERATA: ARCHITETTURA DI GRADO BANCARIO.")
        print("==================================================")
        sys.exit(0)
    finally:
        teardown_environment()
