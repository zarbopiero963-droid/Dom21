import os
import logging

class LedgerGuard:
    logger = logging.getLogger("LedgerGuard")

    @classmethod
    def pre_commit_check(cls, conn):
        try:
            dups = conn.execute("SELECT tx_id FROM journal GROUP BY tx_id HAVING COUNT(id) > 1").fetchone()
            if dups:
                cls.logger.critical(f"💀 FATAL INVARIANT 2 VIOLATO: Double Spend! TX_ID: {dups['tx_id']}. KILLED.")
                os._exit(1)
        except SystemExit:
            raise
        except Exception as e:
            cls.logger.critical(f"💀 GUARD ERROR: Errore verifica invarianti Python-side ({e}). KILLED.")
            os._exit(1)

    @classmethod
    def assert_transition(cls, conn, tx_id, target_status):
        if target_status == "SETTLED":
            row = conn.execute("SELECT status FROM journal WHERE tx_id=?", (tx_id,)).fetchone()
            if not row:
                cls.logger.critical(f"💀 FATAL INVARIANT 3 VIOLATO: Tx {tx_id} inesistente. KILLED.")
                os._exit(1)
            if row["status"] != "PLACED":
                cls.logger.critical(f"💀 FATAL INVARIANT 3 VIOLATO: Transizione illegale {row['status']} -> SETTLED. KILLED.")
                os._exit(1)

    @classmethod
    def handle_db_error(cls, error):
        cls.logger.critical(f"💀 FATAL DB CONSTRAINT VIOLATO: {error}. ROLLBACK FORZATO. KILLED.")
        os._exit(1)
