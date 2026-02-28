import re
import logging

# Whitelist espansa per sintassi Playwright/XPath
SAFE_SELECTOR = re.compile(r"^[a-zA-Z0-9\.\#\-\_\[\]\=\s\:\(\)\"\'>@\*\/\^\$\~\|\+]+$")

def validate_selector(selector: str) -> bool:
    """
    Valida un selettore Playwright/CSS/XPath.
    Include normalizzazione per sventare evasioni XSS o esecuzione arbitraria.
    """
    if not selector:
        return False
    
    # 1. Check Lunghezza (Anti-DoS RegExp)
    if len(selector) > 300: 
        return False
    
    # 2. Hardening: Normalizzazione stringa per pattern matching (rimuove spazi, tab, newline)
    normalized = re.sub(r'[\s\n\r]+', '', selector.lower())
    
    # Blacklist estesa e pattern bloccanti
    blacklist = [
        "javascript:", "vbscript:", "data:text", 
        "onerror=", "onclick=", "onload=", 
        "eval(", "settimeout(", "setinterval("
    ]
    
    if any(bad in normalized for bad in blacklist):
        return False
        
    # Impedisce la selezione diretta di tag eseguibili tramite XPath/CSS
    if "<script" in normalized or "///script" in normalized or "//script" in normalized:
        return False
    
    # 3. Check Whitelist caratteri strutturali
    if not SAFE_SELECTOR.match(selector):
        return False
        
    return True