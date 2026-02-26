import time
import logging
import traceback
import re
import threading
from typing import Dict, Any


class ExecutionEngine:
    def __init__(self, bus, executor, logger=None):
        self.bus = bus
        self.executor = executor
        self.logger = logger or logging.getLogger("ExecutionEngine")
        self.betting_enabled = False
        
        # Sincronizzazione Hedge-Grade
        self.sem = threading.Semaphore(1)
        self._processing_lock = threading.Lock()
        self._processing_matches = set()
        
        # Lock di Stato per variabili concorrenti Watchdog vs Main Thread
        self._state_lock = threading.Lock()
        
        # Stato di sicurezza & Circuit Breaker
        self.consecutive_crashes = 0
        self.last_activity = time.time()
        self.breaker_time = 0
        self.breaker_cooldown = 600  # 10 minuti di castigo
        self.last_breaker_reason = ""
        
        # Deadlock Watchdog Interno
        self.max_bet_time = 120
        self.current_bet_start = 0
        self.current_tx_id = None            
        self.current_money_manager = None    
        self.force_abort = False             
        
        # Avvio del guardiano asincrono
        threading.Thread(target=self._engine_watchdog, daemon=True).start()

    def _engine_watchdog(self):
        """Monitora i deadlock interni al semaphore e gestisce l'auto-recovery in modo Thread-Safe."""
        while True:
            time.sleep(5)
            
            with self._state_lock:
                is_enabled = getattr(self, "betting_enabled", False)
                brk_time = getattr(self, "breaker_time", 0)
                bet_start = getattr(self, "current_bet_start", 0)
                tx = getattr(self, "current_tx_id", None)
                mm = getattr(self, "current_money_manager", None)
            
            if not is_enabled and brk_time > 0:
                if time.time() - brk_time > self.breaker_cooldown:
                    if bet_start != 0:
                        self.logger.warning("⏳ Cooldown terminato, ma Thread Zombie ancora bloccato. Attendo liberazione risorse.")
                        continue
                        
                    self.logger.warning("🔄 Breaker cooldown terminato (10 min). Riattivazione automatica dell'Engine.")
                    with self._state_lock:
                        self.consecutive_crashes = 0
                        self.betting_enabled = True
                        self.breaker_time = 0
                        self.last_breaker_reason = ""
                        self.force_abort = False
                    continue

            if not is_enabled or bet_start == 0:
                continue

            elapsed = time.time() - bet_start
            if elapsed > self.max_bet_time:
                self.logger.critical(f"💀 DEADLOCK BET DETECTED >{self.max_bet_time}s")
                
                if tx and mm:
                    try:
                        mm.refund(tx)
                        self.logger.critical(f"🚑 Zombie Reserve Rimborsata in emergenza dal Watchdog: {tx[:8]}")
                    except Exception as e:
                        self.logger.error(f"Errore Watchdog refund: {e}")
                        
                self.logger.critical("🔌 ENGINE AUTO-SHUTDOWN PER SICUREZZA")
                
                with self._state_lock:
                    self.force_abort = True  
                    self.current_bet_start = 0
                    self.current_tx_id = None
                    self.current_money_manager = None
                    
                self.trip_breaker("DEADLOCK BET TIMEOUT", force_stop=True)

    def trip_breaker(self, reason="unknown", force_stop=False):
        """Hard Circuit Breaker centralizzato con Auto-Recovery timer."""
        self.consecutive_crashes += 1
        self.last_breaker_reason = reason
        self.logger.critical(f"🛑 CIRCUIT BREAKER EVENT: {reason} | Fails: {self.consecutive_crashes}")
        
        if self.consecutive_crashes >= 3 or force_stop:
            self.logger.critical("🔌 CIRCUIT BREAKER HARD STOP. Motore disattivato (Cooldown: 10 min).")
            self.betting_enabled = False
            self.consecutive_crashes = 3
            self.breaker_time = time.time()

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
        
        with self._state_lock:
            if self.force_abort:
                self.logger.warning("⚠️ Reset force_abort stale flag (pre-flight cleanup)")
                self.force_abort = False
            self.current_money_manager = money_manager
            
        self.logger.info(f"⚙️ Avvio processing segnale: {payload.get('teams')}")

        if self.consecutive_crashes >= 3:
            self.logger.critical(f"🛑 CIRCUIT BREAKER TRIPPED! ({self.last_breaker_reason}). Motore SPENTO.")
            self.betting_enabled = False
            return

        if not getattr(self, "betting_enabled", False):
            self.logger.warning("⛔ Betting disabilitato. Segnale ignorato.")
            return

        if not payload.get("is_active", True):
            self.logger.info("⏸️ Robot IN PAUSA → Segnale scartato.")
            return

        teams = payload.get("teams") or "" 
        teams_lower = str(teams).lower()

        with self._processing_lock:
            if teams_lower and teams_lower in self._processing_matches:
                self.logger.warning(f"⛔ Race Condition Bloccata: Il match '{teams}' è già in fase di navigazione.")
                self.bus.emit("BET_FAILED", {"reason": "Concurrent Duplicate Bombing"})
                return
            if teams_lower:
                self._processing_matches.add(teams_lower)

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
                    if hasattr(self.executor, "ensure_login"):
                        self.executor.ensure_login()

                    is_open = False
                    for _ in range(2):
                        if hasattr(self.executor, "check_open_bet"):
                            is_open = self.executor.check_open_bet()
                            if is_open: break
                        time.sleep(1.0)
                        self.last_activity = time.time()

                    market = payload.get("market", "")
                    raw_text = str(payload.get("raw_text", "")).lower()
                    is_live = ("live" in raw_text or "⌚" in raw_text or "m" in raw_text or "gol" in raw_text)
                    
                    pending_list = money_manager.pending()
                    for p in pending_list:
                        p_teams = str(p.get("teams", "")).lower()
                        if p_teams and (p_teams in teams_lower or teams_lower in p_teams):
                            self.logger.warning(f"⛔ Match '{teams}' già prenotato nel DB. Duplicazione bloccata.")
                            self.bus.emit("BET_FAILED", {"reason": "Duplicate match in DB"})
                            return

                    self.last_activity = time.time()
                    nav_ok = self.executor.navigate_to_match(teams, is_live=is_live)
                    if not nav_ok:
                        self.bus.emit("BET_FAILED", {"reason": "Match not found"})
                        return

                    raw_odds = self.executor.find_odds(teams, market)
                    odds = self._safe_float(raw_odds)
                    if odds <= 0:
                        self.bus.emit("BET_FAILED", {"reason": "Odds not found or invalid"})
                        return

                    mm_mode = payload.get("mm_mode", "Stake Fisso")
                    if mm_mode == "Roserpina (Progressione)":
                        decision = money_manager.get_stake(odds, teams=teams)
                        stake = decision.get("stake", 0.0)
                        table_id = decision.get("table_id", 0)
                        tx_id = decision.get("tx_id")
                        
                        if stake <= 0 or table_id == 0 or not tx_id:
                            self.logger.warning("⛔ Risk Engine ha bloccato la scommessa.")
                            self.bus.emit("BET_FAILED", {"reason": "Risk Engine Blocked"})
                            return
                    else:
                        stake = self._safe_float(payload.get("stake", 2.0))
                        if stake <= 0:
                            self.bus.emit("BET_FAILED", {"reason": "Fixed stake invalid"})
                            return

                    balance_before = self._safe_float(self.executor.get_balance())
                    if balance_before > 0 and balance_before < stake:
                        self.logger.error(f"❌ Saldo insufficiente ({balance_before} < {stake})")
                        if tx_id: money_manager.refund(tx_id)
                        self.bus.emit("BET_FAILED", {"reason": "Insufficient real balance"})
                        return

                    if mm_mode != "Roserpina (Progressione)":
                        tx_id = money_manager.reserve(stake, table_id=table_id, teams=teams)
                    
                    with self._state_lock:
                        self.current_tx_id = tx_id

                    # --- ESECUZIONE (Hedge-Grade Patch) ---
                    self.last_activity = time.time()
                    try:
                        bet_ok = self.executor.place_bet(teams, market, stake)
                        if bet_ok:
                            bet_placed = True  # 🔴 FIX FINALE ISTITUZIONALE: Set immediato
                        self.last_activity = time.time()
                    except Exception as e:
                        if not bet_placed:  # 🔴 Nessun refund fatale se bet_placed è True
                            money_manager.refund(tx_id)
                        raise

                    with self._state_lock:
                        if self.force_abort:
                            raise RuntimeError("ZOMBIE THREAD ABORTED: Il Watchdog ha già rimborsato questa operazione.")

                    # 🔒 Conferma logica
                    if bet_placed:
                        self.logger.info(f"✅ Bet certificata dal bookmaker: {stake}€")
                    else:
                        raise RuntimeError("Bet not confirmed by executor")

                    if hasattr(self.executor, "bet_count"): 
                        self.executor.bet_count += 1
                        
                    self.consecutive_crashes = 0
                    self.breaker_time = 0
                    self.last_breaker_reason = ""
                    
                    self.bus.emit("BET_SUCCESS", {"tx_id": tx_id, "teams": teams, "stake": stake, "odds": odds})

                except Exception as e:
                    is_watchdog_abort = False
                    with self._state_lock:
                        is_watchdog_abort = self.force_abort
                    
                    if not is_watchdog_abort:
                        self.trip_breaker(f"Crash runtime: {e}")
                        
                        # 🔴 FIX FINALE: Distinzione vitale tra abort sicuro e bet reale
                        if tx_id and not bet_placed:
                            money_manager.refund(tx_id)
                            self.logger.warning(f"🔄 Rollback TX {tx_id[:8]}")
                        elif tx_id and bet_placed:
                            self.logger.critical(f"☠️ Bet reale effettuata {tx_id[:8]} - Nessun Rollback!")

                    if hasattr(self.executor, "save_blackbox"):
                        try:
                            self.executor.save_blackbox(
                                tx_id, str(e), payload, stake=stake,
                                quota=odds if "odds" in locals() else 0,
                                saldo_db=money_manager.bankroll(),
                                saldo_book=self.executor.get_balance(),
                            )
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
