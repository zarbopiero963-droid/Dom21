import sys
import os
import asyncio
import time
import signal

# =========================================================
# PATH FIX 
# =========================================================
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from core.anti_detect import AntiDetect

print("\n" + "🕵️ " * 20)
print(" AUDIT: AGGANCIO PROFILO DEFAULT REALE V2 ")
print("🕵️ " * 20 + "\n")

async def run_audit():
    context = None
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        print("❌ Playwright non installato.")
        sys.exit(1)

    async with async_playwright() as p:
        # 🔴 PUNTA ALLA TUA VERA CARTELLA DATI DI CHROME
        user_data_path = os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\User Data")
        
        # 🛡️ Argomenti per massimizzare la realtà
        stealth_args = [
            '--disable-blink-features=AutomationControlled',
            '--start-maximized', 
            '--no-sandbox',
            '--disable-infobars'
        ]

        print(f"🚀 Lancio del TUO Chrome reale da: {user_data_path}")
        print("⚠️ RICORDA: Chiudi ogni altra finestra di Chrome prima di procedere!")
        print("🛑 PREMI CTRL+C PER CHIUDERE E RILASCIARE IL PROFILO.")

        try:
            # Avvio con il profilo "Default" (il tuo principale)
            context = await p.chromium.launch_persistent_context(
                user_data_dir=user_data_path,
                executable_path=r"C:\Program Files\Google\Chrome\Application\chrome.exe",
                headless=False,
                args=stealth_args,
                no_viewport=True, 
                ignore_default_args=["--enable-automation"] 
            )
            
            # 💉 INIEZIONE STEALTH (Fondamentale per passare i test)
            stealth_js = """
                Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
                window.chrome = { runtime: {} };
                const getParameter = WebGLRenderingContext.prototype.getParameter;
                WebGLRenderingContext.prototype.getParameter = function(parameter) {
                    if (parameter === 37445) return 'Intel Inc.';
                    if (parameter === 37446) return 'Intel Iris OpenGL Engine';
                    return getParameter(parameter);
                };
            """
            await context.add_init_script(stealth_js)

            page = context.pages[0] if context.pages else await context.new_page()
            
            # Vai su Bet365
            print("🌐 Navigazione su Bet365...")
            await page.goto("https://www.bet365.it/#/HO/", timeout=60000)
            
            print("\n✅ Aggancio riuscito. Ora sei dentro il TUO browser reale.")
            
            # Loop infinito che resta in ascolto del segnale di stop
            while True:
                await asyncio.sleep(1)

        except asyncio.CancelledError:
            pass 
        except Exception as e:
            print(f"❌ ERRORE: {e}")
        finally:
            if context:
                print("\n🔒 Chiusura browser e rilascio Lock profilo...")
                await context.close()

if __name__ == "__main__":
    # Gestione pulita del CTRL+C su Windows/Linux
    try:
        asyncio.run(run_audit())
    except KeyboardInterrupt:
        print("\n👋 Audit terminato dall'utente. Profilo Chrome sbloccato.")
        sys.exit(0)
