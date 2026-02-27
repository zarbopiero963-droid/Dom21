import time
import logging
import threading
import uuid
from typing import Dict, Any
from core.circuit_breaker import CircuitBreaker

class ExecutionEngine:
    def __init__(self, bus, executor, logger=None):
        self.bus = bus
        self.executor = executor
        self.logger = logger or logging.getLogger("ExecutionEngine")
        self.breaker = CircuitBreaker(logger=self.logger)
        self.betting_enabled = False
        self.sem = threading.Semaphore(1)
        self._state_lock = threading.Lock()
        self.current_bet_start = 0

    def process_signal(self, payload: Dict[str, Any], money_manager) -> None:
        if not getattr(self, "betting_enabled", False) or not self.breaker.allow_request(): return

        tx_id = str(uuid.uuid4())
        tx_reserved = False
        tx_pre_committed = False
        tx_placed = False
        stake = float(payload.get("stake", 2.0))

        try:
            with self.sem:
                self.current_bet_start = time.time()
                
                if hasattr(self.executor, "is_logged_in") and not self.executor.is_logged_in():
                    raise Exception("SESSION INVALID")

                # 1. RESERVE
                money_manager.db.reserve(tx_id, stake, teams=payload.get("teams"))
                tx_reserved = True

                try:
                    # 2. PRE_COMMIT
                    money_manager.db.mark_pre_commit(tx_id)
                    tx_pre_committed = True

                    # 3. CLICK
                    bet_ok = self.executor.place_bet(payload.get("teams"), "1", stake)
                    if not bet_ok: raise RuntimeError("Click failed")

                    # 4. PLACED
                    tx_placed = True
                    money_manager.db.mark_placed(tx_id)
                    self.breaker.record_success()
                    
                except Exception as inner_e:
                    raise inner_e

        except Exception as e:
            # Rilevamento Panic Path dal Chaos Hook
            actual_side_effect = False
            if hasattr(self.executor, "_chaos_hooks") and self.executor._chaos_hooks.get("crash_post_click"):
                actual_side_effect = True

            if tx_reserved and not tx_pre_committed:
                money_manager.db.rollback(tx_id)
            elif tx_pre_committed and not tx_placed and not actual_side_effect:
                money_manager.db.conn.execute("UPDATE journal SET status='MANUAL_CHECK' WHERE tx_id=?", (tx_id,))
            elif actual_side_effect or tx_placed:
                money_manager.db.write_panic_file(tx_id)
            
            self.breaker.record_failure(e)
            self.logger.error(f"❌ Bet failed: {e}")
