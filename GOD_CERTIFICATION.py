import os
import sys
import subprocess
import time

print("\n" + "🧠" * 40)
print("GOD CERTIFICATION — FULL SYSTEM VALIDATION")
print("🧠" * 40 + "\n")

ROOT = os.path.abspath(os.path.dirname(__file__))

TESTS = [
    # =========================================
    # 1. CORE & RESILIENCE (Integrità Dati)
    # =========================================
    ("ULTRA SYSTEM", "tests/tests/system_integrity/ULTRA_SYSTEM_TEST.py"),
    ("GOD MODE CHAOS", "tests/stress_lab/GOD_MODE_chaos.py"),
    ("ENDURANCE EXTREME", "tests/tests/system_integrity/ENDURANCE_TEST.py"),
    ("REAL ATTACK", "tests/tests/system_integrity/REAL_ATTACK_TEST.py"),

    # =========================================
    # 2. SECURITY & STEALTH (Invisibilità)
    # =========================================
    ("ANTI-DETECT AUDIT", "tests/tests/system_integrity/ANTI_DETECT_AUDIT.py"),

    # =========================================
    # 3. UI & USER EXPERIENCE (Interfaccia)
    # =========================================
    ("MASTER UI", "tests/tests/ui/MASTER_UI_TEST.py"),
]

failures = []
start_time = time.time()

def run_test(name, path):
    print(f"\n🚀 Running: {name}")
    print("-" * 50)

    # Assicurati che il percorso sia assoluto e compatibile con Windows/Mac/Linux
    full_path = os.path.join(ROOT, os.path.normpath(path))

    if not os.path.exists(full_path):
        print(f"⚠️ File non trovato: {full_path}")
        failures.append(f"{name} (file missing)")
        return

    result = subprocess.run(
        [sys.executable, full_path],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,  # Uniamo stdout e stderr per una lettura pulita
        text=True
    )

    print(result.stdout)

    if result.returncode != 0:
        print("❌ FAILED\n")
        failures.append(name)
    else:
        print("🟢 PASSED\n")

# =====================================================
# EXECUTION
# =====================================================
for name, path in TESTS:
    run_test(name, path)

total_time = time.time() - start_time

print("\n" + "=" * 60)

if failures:
    print("🔴 NON CERTIFICATO")
    print("Test falliti:")
    for f in failures:
        print(" -", f)
    print(f"\nTempo totale: {total_time:.1f}s")
    sys.exit(1)
else:
    print("🟢 BOT CERTIFICATO PRODUZIONE")
    print("Architettura Hedge-Grade e Stealth Biomeccanico Validati.")
    print(f"Tempo totale: {total_time:.1f}s")
    sys.exit(0)