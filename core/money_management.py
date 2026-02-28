import threading
import math
import logging

class MoneyManager:
    def __init__(self, db, logger=None):
        self.db = db
        self.logger = logger or logging.getLogger("MoneyManager")
        self._lock = threading.RLock()
        self.max_exposure = 200.0

    def get_stake_and_reserve(self, tx_id, requested_stake, odds, table_id=1, teams=""):
        with self._lock:
            try:
                odds = float(odds)
                if math.isnan(odds) or math.isinf(odds) or odds <= 1.01:
                    raise ValueError(f"Quota invalida: {odds}")

                stake = float(requested_stake)
                if stake <= 0: return 0.0

                pending = self.db.pending()
                if any(p["tx_id"] == tx_id for p in pending):
                    return 0.0

                current_exposure = sum(float(p["amount"]) for p in pending if p["amount"])
                if current_exposure + stake > self.max_exposure:
                    return 0.0

                self.db.reserve(tx_id, stake, table_id, teams)
                return stake
            except Exception as e:
                self.logger.error(f"Errore reserve: {e}")
                return 0.0

    def reconcile_balances(self):
        with self._lock:
            try: self.db.resolve_panics()
            except Exception as e: self.logger.error(f"Errore recon: {e}")