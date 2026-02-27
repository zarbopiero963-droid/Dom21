import time
import logging
from enum import Enum

class BreakerState(Enum):
    CLOSED = "CLOSED"
    OPEN = "OPEN"
    HALF_OPEN = "HALF_OPEN"

class ErrorSeverity(Enum):
    TRANSIENT = 1       # Retry automatico (lag, element not found)
    OPERATIONAL = 2     # Cooldown breve (timeout bookmaker ripetuti)
    STRUCTURAL = 3      # Freeze duro (disk full, panic ledger)

class CircuitBreaker:
    def __init__(self, logger=None):
        self.logger = logger or logging.getLogger("CircuitBreaker")
        self.state = BreakerState.CLOSED
        self.fail_count = 0
        self.last_failure_time = 0
        self.cooldown_until = 0
        self.structural_lock = False

        # Configurazione Tolleranze
        self.transient_threshold = 3
        self.operational_threshold = 3
        self.operational_cooldown = 120 # 2 minuti di pausa
        self.half_open_test_allowed = False

    def classify(self, exception: Exception) -> ErrorSeverity:
        msg = str(exception).lower()

        # Errori Temporanei (Glitch di rete o DOM)
        if "timeout" in msg or "temporarily" in msg or "not found" in msg or "database is locked" in msg:
            return ErrorSeverity.TRANSIENT

        # Errori Strutturali (Rischio Bancarotta)
        if "disk is full" in msg or "corrupt" in msg or "manual_check" in msg or "panic" in msg:
            return ErrorSeverity.STRUCTURAL

        # Tutto il resto è Operativo (es. Cloudflare Ban momentaneo, credenziali saltate)
        return ErrorSeverity.OPERATIONAL

    def allow_request(self) -> bool:
        now = time.time()

        if self.structural_lock:
            return False

        if self.state == BreakerState.OPEN:
            if now >= self.cooldown_until:
                # Il cooldown è finito: entriamo in modalità esplorativa
                self.state = BreakerState.HALF_OPEN
                self.half_open_test_allowed = True
                self.logger.warning("🟡 Breaker HALF-OPEN: Autorizzata UNA singola transazione di test.")
                return True
            return False

        if self.state == BreakerState.HALF_OPEN:
            if self.half_open_test_allowed:
                self.half_open_test_allowed = False
                return True
            # Se siamo in half-open e abbiamo già lanciato il test, blocchiamo le altre finché non sappiamo l'esito
            return False 

        return True

    def record_success(self):
        if self.state != BreakerState.CLOSED:
            self.logger.info("🟢 Breaker CLOSED: Rete e Bookmaker stabili. Operatività ripristinata al 100%.")
        self.fail_count = 0
        self.state = BreakerState.CLOSED
        self.structural_lock = False

    def record_failure(self, exception: Exception):
        severity = self.classify(exception)
        self.fail_count += 1
        self.last_failure_time = time.time()

        self.logger.warning(f"⚠️ Errore rilevato ({severity.name}) - Fail Count: {self.fail_count}")

        # Se eravamo in HALF-OPEN e falliamo di nuovo, torniamo subito in OPEN
        if self.state == BreakerState.HALF_OPEN:
            self.logger.critical("🔴 Il test in HALF-OPEN è fallito. Ritorno in blocco OPEN.")
            self._open(self.operational_cooldown)
            return

        if severity == ErrorSeverity.TRANSIENT:
            if self.fail_count >= self.transient_threshold:
                self.logger.warning("🟠 Troppi glitch di rete. Pausa di raffreddamento.")
                self._open(60) # Pausa breve per i transienti
            return

        if severity == ErrorSeverity.OPERATIONAL:
            if self.fail_count >= self.operational_threshold:
                self.logger.critical("🔴 Troppi errori operativi. Attivazione circuito OPEN.")
                self._open(self.operational_cooldown)
            return

        if severity == ErrorSeverity.STRUCTURAL:
            self.structural_lock = True
            self.state = BreakerState.OPEN
            self.cooldown_until = float("inf")
            self.logger.critical(f"💀 ERRORE STRUTTURALE FATALE: {str(exception)}")
            self.logger.critical("🔌 TRADING CONGELATO A TEMPO INDETERMINATO. Richiesto check manuale.")

    def _open(self, cooldown_seconds):
        self.state = BreakerState.OPEN
        self.cooldown_until = time.time() + cooldown_seconds
