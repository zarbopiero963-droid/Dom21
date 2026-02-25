import os
import sys
import ctypes
import winreg
import getpass

def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

def setup_vps_immortal():
    print("\n" + "="*50)
    print("🌍 SETUP VPS 24/7 (IMMORTALITÀ ASSOLUTA)")
    print("="*50)
    print("Affinché l'interfaccia grafica si avvii da sola dopo un riavvio")
    print("notturno, Windows Server deve bypassare la schermata di blocco.")
    print("Inserisci le credenziali di questa VPS per abilitare l'Auto-Login.\n")
    
    user = input("Username di Windows (es. Administrator): ").strip()
    pwd = getpass.getpass("Password di Windows (non verrà mostrata a schermo): ").strip()
    
    try:
        key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\Winlogon", 0, winreg.KEY_ALL_ACCESS)
        winreg.SetValueEx(key, "AutoAdminLogon", 0, winreg.REG_SZ, "1")
        winreg.SetValueEx(key, "DefaultUserName", 0, winreg.REG_SZ, user)
        if pwd:
            winreg.SetValueEx(key, "DefaultPassword", 0, winreg.REG_SZ, pwd)
        winreg.CloseKey(key)
        print("\n✅ Auto-Login configurato con successo nel Registro di Sistema!")
    except Exception as e:
        print(f"\n❌ Errore durante la configurazione dell'Auto-Login: {e}")
        print("Assicurati di essere Amministratore.")

    _create_task()

def setup_local_pc():
    print("\n" + "="*50)
    print("💻 SETUP PC LOCALE / DOMESTICO")
    print("="*50)
    print("Il bot partirà automaticamente in background con privilegi")
    print("massimi ogni volta che accendi il PC e fai il normale login.\n")
    _create_task()

def _create_task():
    work_dir = os.path.abspath(os.path.dirname(__file__))
    
    # LOGICA SMART: Cerca supervisor.exe, se non c'è usa supervisor.py
    supervisor_exe = os.path.join(work_dir, "supervisor.exe")
    supervisor_py = os.path.join(work_dir, "supervisor.py")
    
    if os.path.exists(supervisor_exe):
        launch_cmd = f'start "" "{supervisor_exe}"'
        print(f"🔍 Rilevato Supervisor compilato (.exe).")
    else:
        python_exe = sys.executable
        launch_cmd = f'start "" "{python_exe}" "{supervisor_py}"'
        print(f"🔍 Rilevato Supervisor sorgente (.py).")

    bat_path = os.path.join(work_dir, "boot_superagent.bat")
    with open(bat_path, "w") as f:
        f.write(f"@echo off\ncd /d \"{work_dir}\"\n{launch_cmd}\nexit")
    
    task_name = "SuperAgent_Hedge_Watchdog"
    command = f'schtasks /create /tn "{task_name}" /tr "\"{bat_path}\"" /sc onlogon /rl highest /f'
    
    print("⏳ Registrazione nel Task Scheduler di Windows...")
    res = os.system(command)
    
    if res == 0:
        print(f"✅ Boot Task inserito con successo! ({task_name})")
    else:
        print("❌ Errore durante la creazione del Task.")

def main():
    print("🛡️ SUPERAGENT OS - DEPLOYMENT TOOL V8.5 🛡️\n")
    
    if not is_admin():
        print("❌ ERRORE: Devi eseguire questo script come Amministratore!")
        print("Fai click col tasto destro sul Terminale -> 'Esegui come Amministratore'.")
        input("\nPremi INVIO per uscire...")
        sys.exit(1)
        
    print("Dove stai installando il bot?")
    print("1) Su una VPS Remota (Richiede hack Auto-Login per sopravvivere ai reboot)")
    print("2) Sul mio PC Fisico (Parte solo quando inserisco io la password)")
    
    scelta = input("\nScelta (1 o 2): ").strip()
    
    if scelta == "1":
        setup_vps_immortal()
    elif scelta == "2":
        setup_local_pc()
    else:
        print("Scelta non valida. Uscita.")
        sys.exit(1)
        
    print("\n🚀 SETUP COMPLETATO. Il sistema è ora indipendente.")
    input("\nPremi INVIO per chiudere...")

if __name__ == "__main__":
    main()