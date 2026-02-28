import time

def attempt_heal_selector(executor, broken_selector, context_name):
    """
    Tenta di curare un selettore usando il CDP AutoMapper in-place.
    """
    lock = getattr(executor, "_browser_lock", None)
    lock_acquired = False
    
    try:
        if lock:
            lock_acquired = lock.acquire(blocking=True)
            
        page = getattr(executor, "page", None)
        if not page:
            return None
            
        cdp = None
        try:
            cdp = page.context.new_cdp_session(page)
            cdp.send("DOM.enable")
        except Exception:
            return None

        try:
            try:
                resp = cdp.send("DOM.getFlattenedDocument", {"depth": -1, "pierce": True})
            except Exception:
                resp = cdp.send("DOM.getFlattenedDocument", {"depth": 4, "pierce": False})
                
            nodes = resp.get("nodes", [])
            return None
            
        except Exception:
            return None
        finally:
            if cdp:
                try: cdp.detach()
                except: pass
    finally:
        if lock_acquired and lock:
            lock.release()