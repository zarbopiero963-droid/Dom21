import time
import logging
import threading
import uuid
import re
from typing import Dict, Any
from core.circuit_breaker import CircuitBreaker

class ExecutionEngine:
    def __init__(self, bus, executor, logger=None):
        self.bus = bus
        self.executor = executor
        self.logger = logger or logging.getLogger("ExecutionEngine")
        self.breaker = CircuitBreaker(logger=self.logger)
        self.betting_enabled = False
        
        self._shutdown_event = threading.Event()
        self._active_tx_lock = threading.Lock()
        self._active_tx = 0
        self._processing_lock = threading.Lock()
        
    def _safe_float(self, val: Any, default: float = 2.0) -> float:
        try:
            clean_str = re.sub(r'[^\d.,-]', '', str(val))
            if not clean_str: return default
            if ',' in clean_str and '.' in clean_str: clean_str = clean_str.replace('.', '').replace(',', '.')
            elif ',' in clean_str: clean_str = clean_str.replace(',', '.')
            return float(clean_str)
        except: return default

    def process_signal(self, payload: Dict[str, Any], money_manager) -> None:
        with self._active_tx_lock: self._active_tx += 1
        try:
            if not getattr(self, "betting_enabled", False) or not self.breaker.allow_request(): return

            tx_id = None
            tx_reserved = tx_pre_committed = tx_placed = False
            teams = payload.get("teams", "Unknown")
            stake = self._safe_float(payload.get("stake"), 2.0)

            if stake <= 0: return

            try:
                with self._processing_lock:
                    tx_id = str(uuid.uuid4())
                    money_manager.db.reserve(tx_id, stake, teams=teams)
                    tx_reserved = True

                    money_manager.db.mark_pre_commit(tx_id)
                    tx_pre_committed = True

                    bet_ok = self.executor.place_bet(teams, "1", stake)
                    if not bet_ok: raise RuntimeError("Click fallito")

                    tx_placed = True
                    money_manager.db.mark_placed(tx_id)
                    self.breaker.record_success()
                    self.bus.emit("BET_SUCCESS", {"tx_id": tx_id, "teams": teams, "stake": stake})

            except Exception as e:
                final_exc = e
                actual_side_effect = False
                if not tx_id: tx_id = f"FAILED_{int(time.time())}"
                
                if hasattr(self.executor, "_chaos_hooks") and self.executor._chaos_hooks.get("crash_post_click"):
                    actual_side_effect = True

                if tx_reserved and not tx_pre_committed:
                    money_manager.db.rollback(tx_id)
                elif tx_pre_committed and not tx_placed and not actual_side_effect:
                    money_manager.db.mark_manual_check(tx_id)
                    final_exc = Exception("PRE_COMMIT UNCERTAINTY")
                elif actual_side_effect or tx_placed:
                    money_manager.db.write_panic_file(tx_id)
                    final_exc = Exception("PANIC Ledger Triggered")

                self.breaker.record_failure(final_exc)
                self.bus.emit("BET_FAILED", {"tx_id": tx_id, "reason": str(final_exc)})
                
        finally:
            with self._active_tx_lock: self._active_tx -= 1

    def stop_engine(self):
        self.betting_enabled = False
        self._shutdown_event.set()
        start = time.time()
        while True:
            with self._active_tx_lock:
                if self._active_tx == 0: break
            if time.time() - start > 30: break
            time.sleep(0.05)