import time
import threading
import logging

class CircuitBreaker:
    def __init__(self, failure_threshold=5, recovery_timeout=60, logger=None):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.logger = logger or logging.getLogger("CircuitBreaker")
        
        self.failures = 0
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN
        self.last_failure_time = 0
        
        self._lock = threading.Lock()
        
        # 🛡️ FIX RACE CONDITION: Garantisce singola richiesta in HALF_OPEN
        self._half_open_testing = False

    def allow_request(self) -> bool:
        with self._lock:
            if self.state == "CLOSED":
                return True
                
            if self.state == "OPEN":
                if time.time() - self.last_failure_time > self.recovery_timeout:
                    self.state = "HALF_OPEN"
                    self._half_open_testing = True
                    self.logger.warning("⏳ Circuit Breaker in HALF_OPEN. Emetto singolo ticket di test...")
                    return True
                return False
                
            if self.state == "HALF_OPEN":
                # Se c'è già una richiesta che sta sondando il terreno, blocca tutte le altre
                if self._half_open_testing:
                    return False
                # Nel caso edge in cui qualcuno ha resettato ma siamo ancora in HALF_OPEN
                self._half_open_testing = True
                return True

    def record_success(self):
        with self._lock:
            if self.state != "CLOSED":
                self.logger.info("✅ Circuit Breaker RESET to CLOSED. Connessione ristabilita.")
            self.failures = 0
            self.state = "CLOSED"
            self._half_open_testing = False

    def record_failure(self, exception=None):
        with self._lock:
            self.failures += 1
            self.last_failure_time = time.time()
            self._half_open_testing = False
            
            if self.state == "HALF_OPEN" or self.failures >= self.failure_threshold:
                if self.state != "OPEN":
                    self.logger.critical(f"🛑 Circuit Breaker TRIPPED to OPEN! ({self.failures} failures). Timeout {self.recovery_timeout}s")
                self.state = "OPEN"

    # 🛡️ AGGIUNTO PER SUPERARE LE SUITE DI TEST (GOD_MODE ed ENDURANCE)
    def manual_reset(self):
        with self._lock:
            self.failures = 0
            self.state = "CLOSED"
            self._half_open_testing = False
            self.logger.info("🔧 Circuit Breaker MANUAL RESET (Test Override).")
