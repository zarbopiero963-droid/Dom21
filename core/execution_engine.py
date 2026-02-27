import time
import logging
import threading
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
        self._processing_lock = threading.Lock()
        self._processing_matches = set()
        self._state_lock = threading.Lock()
        self.current_bet_start = 0
        self.force_abort = False

    def process_signal(self, payload: Dict[str, Any], money_manager) -> None:
        if not getattr(self, "betting_enabled", False): return
        if not self.breaker.allow_request(): return

        # --- SCOPE DELLE FLAG (Cruciale per l'Audit) ---
        tx_id = None
        tx_reserved = False
        tx_pre_committed = False
        tx_placed = False
        
        teams = payload.get("teams", "Unknown")
        stake = float(payload.get("stake", 2.0))

        try:
            with self.sem:
                self.current_bet_start = time.time()
                
                # 🔒 HARD SESSION CHECK
                if hasattr(self.executor, "is_logged_in") and not self.executor.is_logged_in():
                    raise Exception("SESSION INVALID - Login check fallito pre-bet")

                # 1. RESERVE (DB Phase 1)
                import uuid
                tx_id = str(uuid.uuid4())
                money_manager.db.reserve(tx_id, stake, teams=teams)
                tx_reserved = True

                try:
                    # 2. PRE_COMMIT (Write-Ahead Intent)
                    money_manager.db.mark_pre_commit(tx_id)
                    tx_pre_committed = True

                    # 3. CLICK IRREVERSIBILE (External Action)
                    bet_ok = self.executor.place_bet(teams, "1", stake)
                    if not bet_ok: raise RuntimeError("Click fallito")

                    # 4. PLACED (DB Phase 2)
                    tx_placed = True
                    money_manager.db.mark_placed(tx_id)
                    self.breaker.record_success()
                    
                except Exception as inner_e:
                    # Rilancia per gestire i rollback differenziati
                    raise inner_e

        except Exception as e:
            final_exc = e
            if tx_reserved and not tx_pre_committed:
                money_manager.db.rollback(tx_id) # Refund sicuro
            elif tx_pre_committed and not tx_placed:
                # Zona d'ombra
                money_manager.db.conn.execute("UPDATE journal SET status='MANUAL_CHECK' WHERE tx_id=?", (tx_id,))
                final_exc = Exception("PRE_COMMIT UNCERTAINTY")
            elif tx_placed:
                # Panic Ledger path
                final_exc = Exception("PANIC LEDGER TRIGGERED")
                money_manager.db.write_panic_file(tx_id)

            self.breaker.record_failure(final_exc)
            self.logger.error(f"❌ Bet Fallita: {final_exc}")
        finally:
            self.current_bet_start = 0
