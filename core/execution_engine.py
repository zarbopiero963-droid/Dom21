import time
import logging
import traceback
import re
import threading
from typing import Dict, Any

from core.circuit_breaker import CircuitBreaker

class ExecutionEngine:
    def __init__(self, bus, executor, logger=None):
        self.bus = bus
        self.executor = executor
        self.logger = logger or logging.getLogger("ExecutionEngine")
        self.betting_enabled = False
        
        # Inizializziamo il nuovo Breaker Adattivo
        self.breaker = CircuitBreaker(logger=self.logger)
        
        self.sem = threading.Semaphore(1)
        self._processing_lock = threading.Lock()
        self._processing_matches = set()
        
        self._state_lock = threading.Lock()
        self.last_activity = time.time()
        
        self.max_bet_time = 120
        self.current_bet_start = 0
        self.current_tx_id = None            
        self.current_money_manager = None    
        self.force_abort = False             
        
        threading.Thread(target=self._engine_watchdog, daemon=True).start()

    def _engine_watchdog(self):
        while True:
            time.sleep(5)
            with self._state_lock:
                is_enabled = getattr(self, "betting_enabled", False)
                bet_start = getattr(self, "current_bet_start", 0)
                tx = getattr(self, "current_tx_id", None)
                mm = getattr(self, "current_money_manager", None)

            if not is_enabled or bet_start == 0: continue

            elapsed = time.time() - bet_start
            if elapsed > self.max_bet_time:
                self.logger.critical(f"💀 DEADLOCK BET DETECTED >{self.max_bet_time}s")
                if tx and mm:
                    try:
                        mm.refund(tx)
                        self.logger.critical(f"🚑 Zombie Reserve Rimborsata in emergenza dal Watchdog: {tx[:8]}")
                    except Exception as e:
                        self.logger.error(f"Errore Watchdog refund: {e}")
                self.logger.critical("🔌 ENGINE AUTO-SHUTDOWN PER DEADLOCK")
                with self._state_lock:
                    self.force_abort = True  
                    self.current_bet_start = 0
                    self.current_tx_id = None
                    self.current_money_manager = None
                
                # Registriamo l'errore come operativo nel nuovo breaker
                self.breaker.record_failure(RuntimeError("DEADLOCK BET TIMEOUT"))

    def _safe_float(self, value: Any) -> float:
        if isinstance(value, (int, float)): return float(value)
        if not value: return 0.0
        cleaned = re.sub(r"[^\d,\.]", "", str(value))
        if not cleaned: return 0.0
        if "," in cleaned and "." in cleaned:
            if cleaned.rfind(",") > cleaned.rfind("."):
                cleaned = cleaned.replace(".", "").replace(",", ".")
            else:
                cleaned = cleaned.replace(",", "")
        elif "," in cleaned: cleaned = cleaned.replace(",", ".")
        try: return float(cleaned)
        except ValueError: return 0.0

    def process_signal(self, payload: Dict[str, Any], money_manager) -> None:
        self.last_activity = time.time()
        
        if not getattr(self, "betting_enabled", False) or not payload.get("is_active", True): 
            return

        # 🛡️ INTERROGAZIONE DEL BREAKER ADATTIVO
        if not self.breaker.allow_request():
            self.logger.warning(f"🛑 Breaker {self.breaker.state.name}: Trading bloccato o in cooldown. Segnale ignorato.")
            return

        with self._state_lock:
            if self.force_abort: self.force_abort = False
            self.current_money_manager = money_manager
            
        self.logger.info(f"⚙️ Avvio processing segnale: {payload.get('teams')}")

        teams = payload.get("teams") or "" 
        teams_lower = str(teams).lower()

        with self._processing_lock:
            if teams_lower and teams_lower in self._processing_matches:
                self.bus.emit("BET_FAILED", {"reason": "Concurrent Duplicate Bombing"})
                return
            if teams_lower: self._processing_matches.add(teams_lower)

        try:
            with self.sem:
                with self._state_lock:
                    self.current_bet_start = time.time()
                    self.force_abort = False
                    
                self.last_activity = time.time()
                tx_id = None
                bet_placed = False
                stake = 0.0
                table_id = 1

                try:
                    if hasattr(self.executor, "ensure_login"): self.executor.ensure_login()

                    for _ in range(2):
                        if hasattr(self.executor, "check_open_bet") and self.executor.check_open_bet(): break
                        time.sleep(1.0)
                        self.last_activity = time.time()

                    market = payload.get("market", "")
                    raw_text = str(payload.get("raw_text", "")).lower()
                    is_live = ("live" in raw_text or "⌚" in raw_text or "m" in raw_text or "gol" in raw_text)
                    
                    pending_list = money_manager.pending()
                    for p in pending_list:
                        p_teams = str(p.get("teams", "")).lower()
                        if p_teams and (p_teams in teams_lower or teams_lower in p_teams):
                            self.bus.emit("BET_FAILED", {"reason": "Duplicate match in DB"})
                            return

                    self.last_activity = time.time()
                    if not self.executor.navigate_to_match(teams, is_live=is_live):
                        raise Exception("Match non trovato (Timeout / Not Found)")

                    raw_odds = self.executor.find_odds(teams, market)
                    odds = self._safe_float(raw_odds)
                    if odds <= 0:
                        raise Exception("Quota non trovata (Timeout / Invalid Odds)")

                    mm_mode = payload.get("mm_mode", "Stake Fisso")
                    if mm_mode == "Roserpina (Progressione)":
                        decision = money_manager.get_stake(odds, teams=teams)
                        stake = decision.get("stake", 0.0)
                        table_id = decision.get("table_id", 0)
                        tx_id = decision.get("tx_id")
                        if stake <= 0 or table_id == 0 or not tx_id:
                            self.bus.emit("BET_FAILED", {"reason": "Risk Engine Blocked"})
                            return
                    else:
                        stake = self._safe_float(payload.get("stake", 2.0))
                        if stake <= 0:
                            self.bus.emit("BET_FAILED", {"reason": "Fixed stake invalid"})
                            return

                    balance_before = self._safe_float(self.executor.get_balance())
                    if balance_before > 0 and balance_before < stake:
                        if tx_id: money_manager.refund(tx_id)
                        raise Exception("Saldo reale insufficiente sul bookmaker")

                    if mm_mode != "Roserpina (Progressione)":
                        tx_id = money_manager.reserve(stake, table_id=table_id, teams=teams)
                    
                    with self._state_lock: self.current_tx_id = tx_id

                    # 🛑 ESECUZIONE (2-Phase Commit Patch)
                    self.last_activity = time.time()
                    try:
                        bet_ok = self.executor.place_bet(teams, market, stake)
                        if not bet_ok:
                            raise RuntimeError("Timeout o errore click place_bet")
                            
                        # 🔒 PASSAGGIO FASE 2: Da RESERVED a PLACED
                        bet_placed = True
                        money_manager.db.mark_placed(tx_id)
                        self.last_activity = time.time()
                        
                    except Exception as inner_e:
                        if not bet_placed:
                            money_manager.refund(tx_id)
                        raise inner_e

                    with self._state_lock:
                        if self.force_abort: raise RuntimeError("ZOMBIE THREAD ABORTED")

                    self.logger.info(f"✅ Bet PLACED e certificata dal bookmaker: {stake}€")

                    if hasattr(self.executor, "bet_count"): self.executor.bet_count += 1
                        
                    # 🟢 SUCCESS: Informiamo il breaker che è andato tutto liscio!
                    self.breaker.record_success()
                    
                    self.bus.emit("BET_SUCCESS", {"tx_id": tx_id, "teams": teams, "stake": stake, "odds": odds})

                except Exception as e:
                    # 🔴 FAILURE: Informiamo il breaker dell'errore. Penserà lui a classificare il rischio.
                    self.breaker.record_failure(e)
                    
                    is_watchdog_abort = False
                    with self._state_lock: is_watchdog_abort = self.force_abort
                    
                    if not is_watchdog_abort:
                        if tx_id and not bet_placed:
                            money_manager.refund(tx_id)
                            self.logger.warning(f"🔄 Rollback FASE 1 (RESERVED) eseguito: {tx_id[:8]}")
                        elif tx_id and bet_placed:
                            self.logger.critical(f"☠️ Bet PLACED sul bookmaker {tx_id[:8]} - DB UPDATE FALLITO! Innesco PANIC LEDGER.")
                            # Forziamo un errore strutturale nel breaker per bloccare tutto
                            self.breaker.record_failure(Exception("PANIC LEDGER TRIGGERED"))
                            if hasattr(money_manager.db, 'write_panic_file'):
                                money_manager.db.write_panic_file(tx_id)

                    if hasattr(self.executor, "save_blackbox"):
                        try:
                            self.executor.save_blackbox(tx_id, str(e), payload, stake=stake, quota=odds if "odds" in locals() else 0, saldo_db=money_manager.bankroll(), saldo_book=self.executor.get_balance())
                        except Exception: pass

                    self.bus.emit("BET_FAILED", {"tx_id": tx_id, "reason": str(e)})

                finally:
                    with self._state_lock:
                        self.current_bet_start = 0
                        self.current_tx_id = None
                        self.current_money_manager = None

        finally:
            self.last_activity = time.time()
            with self._processing_lock:
                if teams_lower and teams_lower in self._processing_matches:
                    self._processing_matches.remove(teams_lower)
