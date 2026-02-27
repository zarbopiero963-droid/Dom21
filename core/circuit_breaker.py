import os
import time
import json
import logging
import threading
from enum import Enum
from pathlib import Path

DB_DIR = os.path.join(str(Path.home()), ".superagent_data")
os.makedirs(DB_DIR, exist_ok=True)
STATE_FILE = os.path.join(DB_DIR, "breaker_state.json")

class BreakerState(Enum):
    CLOSED = "CLOSED"
    OPEN = "OPEN"
    HALF_OPEN = "HALF_OPEN"

class ErrorSeverity(Enum):
    TRANSIENT = 1               # Retry automatico (lag, db locked)
    OPERATIONAL = 2             # Cooldown breve (timeout ripetuti)
    STRUCTURAL_RECOVERABLE = 3  # Cooldown lungo (Cloudflare, Login scaduto)
    STRUCTURAL_FATAL = 4        # Freeze duro infinito (Disk full, Panic Ledger)

class CircuitBreaker:
    def __init__(self, logger=None):
        self.logger = logger or logging.getLogger("CircuitBreaker")
        self._io_lock = threading.Lock() # Lock per scritture concorrenti sicure
        
        # ⏱️ Sliding Window & Burst Memory
        self.failures = [] 
        self.window_size = 3600 # 1 ora di memoria globale
        self.burst_window = 60  # 60 secondi per rilevare un picco fatale (Burst)
        
        # Stato Base
        self.state = BreakerState.CLOSED
        self.last_failure_time = 0
        self.cooldown_until = 0
        self.structural_lock = False
        
        # 🐕 HALF-OPEN Watchdog
        self.half_open_test_allowed = False
        self.half_open_start_time = 0
        self.half_open_timeout = 180 # Max 3 min per la transazione di test
        
        # ⚖️ Soglie Tolleranza Adattive
        self.burst_threshold = 3      # Se >=3 errori in <60s -> OPEN immediato
        self.sustained_threshold = 5  # Se >=5 errori in <1h -> OPEN
        self.operational_cooldown = 120 
        self.recoverable_cooldown = 600 
        
        self._load_state()

    # =============================
    # GESTIONE STATO & PERSISTENZA ATOMICA
    # =============================

    def manual_reset(self):
        """Override amministrativo per sbloccare i STRUCTURAL_FATAL."""
        with self._io_lock:
            self.state = BreakerState.CLOSED
            self.structural_lock = False
            self.cooldown_until = 0
            self.failures.clear()
            self.half_open_start_time = 0
            self.half_open_test_allowed = False
            self._save_state_unsafe()
        self.logger.critical("🔓 BREAKER MANUAL RESET: Sistema sbloccato forzatamente dall'operatore.")

    def _save_state(self):
        with self._io_lock:
            self._save_state_unsafe()

    def _save_state_unsafe(self):
        """Salva su disco usando scrittura atomica (Temp File + Replace) per evitare file corruzioni in caso di crash OS."""
        state_data = {
            "state": self.state.value,
            "cooldown_until": self.cooldown_until,
            "structural_lock": self.structural_lock,
            "failures": self.failures
        }
        try:
            tmp_file = STATE_FILE + ".tmp"
            with open(tmp_file, "w") as f:
                json.dump(state_data, f)
            os.replace(tmp_file, STATE_FILE) # Operazione atomica kernel-level
        except Exception as e:
            self.logger.error(f"Failed to save breaker state atomically: {e}")

    def _load_state(self):
        with self._io_lock:
            if os.path.exists(STATE_FILE):
                try:
                    with open(STATE_FILE, "r") as f:
                        data = json.load(f)
                    
                    self.state = BreakerState(data.get("state", "CLOSED"))
                    self.cooldown_until = data.get("cooldown_until", 0)
                    self.structural_lock = data.get("structural_lock", False)
                    self.failures = data.get("failures", [])
                    
                    # 🧹 Sanity Check: Pulizia stato stantio al boot
                    now = time.time()
                    if self.state == BreakerState.OPEN and not self.structural_lock and now > self.cooldown_until:
                        self.state = BreakerState.CLOSED
                        self.failures.clear()
                        self.logger.info("🧹 Boot Sanity Check: Cooldown ampiamente scaduto durante il downtime. Breaker resettato a CLOSED.")
                    else:
                        self.logger.info(f"🛡️ Breaker state ripristinato dal disco: {self.state.name}")
                        
                except Exception as e:
                    self.logger.error(f"Failed to load breaker state: {e}")

    # =============================
    # MOTORE LOGICO & SLIDING WINDOW
    # =============================

    def _clean_window(self, now):
        self.failures = [t for t in self.failures if now - t <= self.window_size]

    def _check_rate_limits(self, now) -> bool:
        """Ritorna True se le soglie (Burst o Sustained) sono superate."""
        sustained_count = len(self.failures)
        
        if sustained_count >= self.sustained_threshold:
            self.logger.warning(f"📈 Sustained Rate Superato: {sustained_count} errori in 1h.")
            return True
            
        if sustained_count >= self.burst_threshold:
            burst_start_time = self.failures[-self.burst_threshold]
            if now - burst_start_time <= self.burst_window:
                self.logger.warning(f"💥 Burst Rate Superato: {self.burst_threshold} errori in < {self.burst_window}s.")
                return True
                
        return False

    def classify(self, exception: Exception) -> ErrorSeverity:
        msg = str(exception).lower()
        if "timeout" in msg or "temporarily" in msg or "not found" in msg or "database is locked" in msg:
            return ErrorSeverity.TRANSIENT
        if "cloudflare" in msg or "captcha" in msg or "login" in msg or "session" in msg:
            return ErrorSeverity.STRUCTURAL_RECOVERABLE
        if "disk is full" in msg or "corrupt" in msg or "manual_check" in msg or "panic" in msg:
            return ErrorSeverity.STRUCTURAL_FATAL
        return ErrorSeverity.OPERATIONAL

    def allow_request(self) -> bool:
        now = time.time()
        
        if self.structural_lock:
            return False

        if self.state == BreakerState.OPEN:
            if now >= self.cooldown_until:
                self.state = BreakerState.HALF_OPEN
                self.half_open_test_allowed = True
                self.half_open_start_time = 0
                self._save_state()
                self.logger.warning("🟡 Breaker HALF-OPEN: Autorizzata UNA singola transazione di test.")
                return True
            return False

        if self.state == BreakerState.HALF_OPEN:
            if self.half_open_test_allowed:
                self.half_open_test_allowed = False
                self.half_open_start_time = now
                return True
            else:
                if self.half_open_start_time > 0 and (now - self.half_open_start_time > self.half_open_timeout):
                    self.logger.critical("🔴 HALF-OPEN Watchdog: Test timeout (Transazione appesa). Ritorno in OPEN.")
                    self.record_failure(Exception("HALF-OPEN Test Timeout"))
                return False

        return True

    def record_success(self):
        if self.state != BreakerState.CLOSED:
            self.logger.info("🟢 Breaker CLOSED: Rete/Bookmaker stabili. Operatività ripristinata al 100%.")
        
        with self._io_lock:
            self.failures.clear()
            self.state = BreakerState.CLOSED
            self.structural_lock = False
            self.half_open_start_time = 0
            self._save_state_unsafe()

    def record_failure(self, exception: Exception):
        now = time.time()
        severity = self.classify(exception)
        self.last_failure_time = now
        
        with self._io_lock:
            self.failures.append(now)
            self._clean_window(now)
            current_failures_count = len(self.failures)
        
        self.logger.warning(f"⚠️ Errore rilevato ({severity.name}) - Errori attivi in finestra: {current_failures_count}")

        if self.state == BreakerState.HALF_OPEN:
            self.logger.critical("🔴 Il test in HALF-OPEN è fallito. Ritorno immediato in blocco OPEN.")
            self._open(self.operational_cooldown)
            return

        if severity == ErrorSeverity.STRUCTURAL_FATAL:
            self.structural_lock = True
            self.state = BreakerState.OPEN
            self.cooldown_until = float("inf")
            self.logger.critical(f"💀 ERRORE STRUTTURALE FATALE: {str(exception)}")
            self.logger.critical("🔌 TRADING CONGELATO A TEMPO INDETERMINATO. Eseguire `manual_reset()` dopo fix.")
            self._save_state()
            return
            
        if severity == ErrorSeverity.STRUCTURAL_RECOVERABLE:
            self.logger.critical(f"🟠 Errore Strutturale Recuperabile. Cooldown lungo: {self.recoverable_cooldown}s.")
            self._open(self.recoverable_cooldown)
            return

        # TRANSIENT e OPERATIONAL valutati con Burst/Sustained logic
        if self._check_rate_limits(now):
            cooldown = 60 if severity == ErrorSeverity.TRANSIENT else self.operational_cooldown
            self.logger.warning(f"🛑 Soglia rateo errori superata. Attivazione circuito OPEN ({cooldown}s).")
            self._open(cooldown)
        else:
            self._save_state() 

    def _open(self, cooldown_seconds):
        self.state = BreakerState.OPEN
        self.cooldown_until = time.time() + cooldown_seconds
        self._save_state()
