import subprocess
import time
import sys
import os
import datetime

def log_event(msg):
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] 👁️ WATCHDOG: {msg}")
    
    # Scrive anche su file per poter debuggare crash notturni
    with open("supervisor_crash.log", "a", encoding="utf-8") as f:
        f.write(f"[{timestamp}] {msg}\n")

def run_watchdog():
    log_event("Avvio Supervisor di sistema.")
    
    # --- LOGICA SMART PER EXE ---
    # Inserisci qui il nome esatto del tuo file exe (es. "bot.exe", "main.exe")
    exe_names = ["SuperAgent.exe", "main.exe", "bot.exe"]
    target_cmd = None

    for name in exe_names:
        if os.path.exists(name):
            target_cmd = [os.path.abspath(name)]
            break
            
    # Se non trova nessun EXE, usa il file python di default
    if not target_cmd:
        target_cmd = [sys.executable, os.path.abspath("main.py")]

    log_event(f"Eseguibile bersaglio rilevato: {target_cmd[0]}")
    
    consecutive_crashes = 0
    
    while True:
        log_event("Lancio applicazione SuperAgent Core...")
        
        # Lancia l'EXE (o il PY) e resta in ascolto
        process = subprocess.Popen(target_cmd)
        
        # Il supervisor si blocca qui e aspetta che il bot muoia
        process.wait()
        
        exit_code = process.returncode
        log_event(f"SuperAgent terminato. Codice di uscita: {exit_code}")
        
        if exit_code == 0:
            # Codice 0 significa che hai chiuso tu l'app volontariamente con la "X"
            log_event("Spegnimento umano rilevato. Interruzione Supervisor in corso.")
            break
        else:
            # Qualsiasi altro codice significa CRASH!
            consecutive_crashes += 1
            
            wait_time = min(consecutive_crashes * 5, 60)
            
            log_event(f"🔥 CRASH ANOMALO RILEVATO! (Crash n.{consecutive_crashes})")
            log_event(f"Rianimazione forzata del sistema in {wait_time} secondi...")
            
            time.sleep(wait_time)

if __name__ == "__main__":
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    run_watchdog()