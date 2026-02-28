def attempt_heal_selector(executor, broken_selector, context_name):
    lock = getattr(executor, "_browser_lock", None)
    lock_acquired = False
    
    try:
        if lock: lock_acquired = lock.acquire(blocking=True)
            
        page = getattr(executor, "page", None)
        if not page: return None
            
        cdp = None
        try:
            cdp = page.context.new_cdp_session(page)
            cdp.send("DOM.enable")
        except: return None

        try:
            try: resp = cdp.send("DOM.getFlattenedDocument", {"depth": -1, "pierce": True})
            except: resp = cdp.send("DOM.getFlattenedDocument", {"depth": 4, "pierce": False})
            return None
        except: return None
        finally:
            if cdp:
                try: cdp.detach()
                except: pass
    finally:
        if lock_acquired and lock: lock.release()