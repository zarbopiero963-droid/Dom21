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

                # 🛡️ FIX ARCHITETTURALE: Controllo deterministico sul bankroll reale
                current_balance, _ = self.db.get_balance()
                
                if stake > current_balance:
                    self.logger.warning(f"Stake {stake}€ rifiutato: supera il saldo disponibile ({current_balance}€).")
                    return 0.0

                # L'esposizione logica viene calcolata solo se ci sono i fondi reali
                current_exposure = sum(float(p["amount"]) for p in pending if p["amount"])
                if current_exposure + stake > self.max_exposure:
                    self.logger.warning(f"Stake {stake}€ rifiutato: supera la max_exposure ({self.max_exposure}€).")
                    return 0.0

                # Esecuzione atomica garantita
                self.db.reserve(tx_id, stake, table_id, teams)
                return stake
            except Exception as e:
                self.logger.error(f"Errore critico durante reserve: {e}")
                return 0.0

    def reconcile_balances(self):
        with self._lock:
            try: self.db.resolve_panics()
            except Exception as e: self.logger.error(f"Errore riconciliazione: {e}")

    # 🛡️ Backward Compatibility per ULTRA_SYSTEM_TEST e Execution Engine
    def refund(self, tx_id: str):
        """
        Esegue il rollback sicuro di una transazione RESERVED in caso di abort.
        """
        with self._lock:
            try:
                self.db.rollback(tx_id)
                self.logger.info(f"Refund eseguito con successo per TX {tx_id}")
            except Exception as e:
                self.logger.error(f"Refund fallito per TX {tx_id}: {e}")
                raise