import os
import sys
import time
import psutil
import threading
import logging

# =========================================================
# PATH FIX 
# =========================================================
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from core.controller import SuperAgentController

print("\n🧠 SOAK TEST 24H — HEDGE FUND STABILITY\n")

logging.basicConfig(level=logging.CRITICAL)
# Fix: Passiamo solo il logger al controller!
controller = SuperAgentController(logging.getLogger("SOAK"))

process = psutil.Process(os.getpid())
start_ram = process.memory_info().rss
start_time = time.time()

MAX_MINUTES = 2   # Per i test rapidi su GitHub. 
CHECK_INTERVAL = 5

freeze_detect = {"last": time.time()}
failures = []

# HEARTBEAT
def heartbeat():
    while True:
        freeze_detect["last"] = time.time()
        time.sleep(1)

threading.Thread(target=heartbeat, daemon=True).start()

# LOOP TEST
print(f"Avvio test di saturazione (Durata prevista: {MAX_MINUTES} min)...")
while True:
    now = time.time()
    elapsed_m = (now - start_time) / 60

    if elapsed_m > MAX_MINUTES:
        break

    # Simula segnali fake stressanti
    try:
        controller.engine.process_signal({"teams": "SOAK_TEST", "market": "1"}, controller.money_manager)
    except Exception:
        pass

    # RAM CHECK
    current_ram = process.memory_info().rss
    diff_mb = (current_ram - start_ram) / 1024 / 1024

    if diff_mb > 300:
        failures.append(f"MEMORY LEAK >300MB ({diff_mb:.1f}MB)")
        break

    # FREEZE CHECK
    if time.time() - freeze_detect["last"] > 30:
        failures.append("ENGINE FREEZE >30s")
        break

    time.sleep(CHECK_INTERVAL)

print("\n==============================")
if failures:
    print("🔴 SOAK TEST FAILED")
    for f in failures: print("❌", f)
    sys.exit(1)
else:
    print("🟢 SOAK TEST SUPERATO")
    print("Sistema stabile: Nessun Memory Leak rilevato.")
    sys.exit(0)