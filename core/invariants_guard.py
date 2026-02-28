import os
import logging

class LedgerGuard:
    logger = logging.getLogger("LedgerGuard")

    @classmethod
    def pre_commit_check(cls, conn):
        try:
            dups = conn.execute("SELECT tx_id FROM journal GROUP BY tx_id HAVING COUNT(id) > 1").fetchone()
            if dups:
                cls.logger.critical(f"💀 FATAL INVARIANT 2 VIOLATO: Double Spend! TX_ID: {dups['tx_id']}.")
                cls._trigger_kill_switch(RuntimeError(f"Double Spend Detected: {dups['tx_id']}"))
        except SystemExit:
            raise
        except Exception as e:
            cls.logger.critical(f"💀 GUARD ERROR: Errore verifica invarianti Python-side ({e}).")
            cls._trigger_kill_switch(e)

    @classmethod
    def assert_transition(cls, conn, tx_id, target_status):
        if target_status == "SETTLED":
            row = conn.execute("SELECT status FROM journal WHERE tx_id=?", (tx_id,)).fetchone()
            if not row:
                cls.logger.critical(f"💀 FATAL INVARIANT 3 VIOLATO: Tx {tx_id} inesistente.")
                cls._trigger_kill_switch(RuntimeError("Tx inesistente"))
            if row["status"] != "PLACED":
                cls.logger.critical(f"💀 FATAL INVARIANT 3 VIOLATO: Transizione illegale {row['status']} -> SETTLED.")
                cls._trigger_kill_switch(RuntimeError("Transizione illegale"))

    @classmethod
    def handle_db_error(cls, error):
        cls.logger.critical(f"💀 FATAL DB CONSTRAINT VIOLATO: {error}. ROLLBACK FORZATO.")
        cls._trigger_kill_switch(error)

    @classmethod
    def _trigger_kill_switch(cls, error):
        """
        Gestore unificato della morte del processo.
        Modalità Test-Safe: Lancia l'eccezione.
        Modalità Banca Centrale (Prod): Uccide il processo a livello OS.
        """
        if os.environ.get("CI") == "true" or os.environ.get("ALLOW_DB_EXCEPTION") == "1":
            cls.logger.warning("🧪 [CI MODE ATTIVO] Bypass os._exit(1) -> Sollevo eccezione per PyTest.")
            raise error
        
        cls.logger.critical("🔌 [PROD MODE] STACCO LA CORRENTE. KILLED.")
        os._exit(1)