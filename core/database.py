import os
import time
import logging
import threading
import sqlite3
import math
from pathlib import Path

DB_DIR = os.path.join(str(Path.home()), ".superagent_data")
os.makedirs(DB_DIR, exist_ok=True)
DB_PATH = os.path.join(DB_DIR, "money_db.sqlite")

class Database:
    def __init__(self):
        self.conn = sqlite3.connect(DB_PATH, check_same_thread=False, timeout=30, isolation_level=None)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA journal_mode=WAL;")
        self.conn.execute("PRAGMA synchronous=NORMAL;")
        self._lock = threading.RLock()
        self._write_lock = threading.Lock()
        self._init_db()

    def _init_db(self):
        with self._write_lock:
            with self._lock:
                self.conn.execute("""
                    CREATE TABLE IF NOT EXISTS journal (
                        id INTEGER PRIMARY KEY AUTOINCREMENT, 
                        tx_id TEXT UNIQUE, 
                        amount REAL, 
                        status TEXT, 
                        payout REAL DEFAULT 0, 
                        timestamp INTEGER, 
                        table_id INTEGER DEFAULT 1, 
                        teams TEXT DEFAULT '',
                        match_hash TEXT DEFAULT ''
                    )
                """)
                self.conn.execute("CREATE TABLE IF NOT EXISTS balance (id INTEGER PRIMARY KEY CHECK (id = 1), current_balance REAL, peak_balance REAL DEFAULT 1000.0)")
                self.conn.execute("INSERT OR IGNORE INTO balance (id, current_balance, peak_balance) VALUES (1, 1000.0, 1000.0)")

    def get_balance(self):
        with self._lock:
            row = self.conn.execute("SELECT current_balance, peak_balance FROM balance WHERE id = 1").fetchone()
            return (float(row["current_balance"]), float(row["peak_balance"])) if row else (0.0, 0.0)

    def update_bankroll(self, current_balance, peak_balance):
        with self._write_lock:
            with self._lock:
                self.conn.execute("BEGIN IMMEDIATE")
                try:
                    self.conn.execute(
                        "UPDATE balance SET current_balance=?, peak_balance=? WHERE id=1", 
                        (float(current_balance), float(peak_balance))
                    )
                    self.conn.execute("COMMIT")
                except:
                    self.conn.execute("ROLLBACK")
                    raise

    def reserve(self, tx_id, amount, table_id=1, teams="", match_hash=""):
        try:
            amt = float(amount)
            if math.isnan(amt) or math.isinf(amt) or amt <= 0:
                raise ValueError(f"Stake non valido o corrotto: {amount}")
        except (TypeError, ValueError):
            raise ValueError("Stake impossibile da convertire")

        with self._write_lock:
            with self._lock:
                self.conn.execute("BEGIN IMMEDIATE")
                try:
                    # 🛡️ FIX ZOMBIE_TX: Protezione saldo negativo
                    row = self.conn.execute("SELECT current_balance FROM balance WHERE id = 1").fetchone()
                    if not row or float(row["current_balance"]) < float(amt):
                        raise ValueError(f"Fondi insufficienti. Richiesti {amt}, disponibili {row['current_balance'] if row else 'N/A'}")

                    self.conn.execute("""
                        INSERT INTO journal (tx_id, amount, status, timestamp, table_id, teams, match_hash)
                        VALUES (?, ?, 'RESERVED', ?, ?, ?, ?)
                    """, (tx_id, amt, int(time.time()), table_id, teams, match_hash))
                    self.conn.execute("UPDATE balance SET current_balance = current_balance - ? WHERE id = 1", (amt,))
                    self.conn.execute("COMMIT")
                except:
                    self.conn.execute("ROLLBACK")
                    raise

    def mark_pre_commit(self, tx_id):
        with self._write_lock:
            with self._lock:
                self.conn.execute("BEGIN IMMEDIATE")
                try:
                    self.conn.execute("UPDATE journal SET status='PRE_COMMIT' WHERE tx_id=?", (tx_id,))
                    self.conn.execute("COMMIT")
                except:
                    self.conn.execute("ROLLBACK")
                    raise

    def mark_placed(self, tx_id):
        with self._write_lock:
            with self._lock:
                self.conn.execute("BEGIN IMMEDIATE")
                try:
                    self.conn.execute("UPDATE journal SET status='PLACED' WHERE tx_id=?", (tx_id,))
                    self.conn.execute("COMMIT")
                except:
                    self.conn.execute("ROLLBACK")
                    raise

    def pending(self):
        with self._lock:
            return [dict(r) for r in self.conn.execute("SELECT * FROM journal WHERE status NOT IN ('VOID', 'SETTLED')").fetchall()]

    def get_unsettled_placed(self):
        with self._lock:
            return [dict(r) for r in self.conn.execute("SELECT * FROM journal WHERE status='PLACED'").fetchall()]

    def rollback(self, tx_id):
        with self._write_lock:
            with self._lock:
                self.conn.execute("BEGIN IMMEDIATE")
                try:
                    row = self.conn.execute("SELECT amount FROM journal WHERE tx_id = ? AND status = 'RESERVED'", (tx_id,)).fetchone()
                    if row and row["amount"] is not None:
                        self.conn.execute("UPDATE journal SET status = 'VOID' WHERE tx_id = ?", (tx_id,))
                        self.conn.execute("UPDATE balance SET current_balance = current_balance + ? WHERE id = 1", (float(row["amount"]),))
                    self.conn.execute("COMMIT")
                except:
                    self.conn.execute("ROLLBACK")
                    raise

    def recover_reserved(self):
        with self._write_lock:
            with self._lock:
                self.conn.execute("BEGIN IMMEDIATE")
                try:
                    rows = self.conn.execute("SELECT tx_id, amount FROM journal WHERE status='RESERVED'").fetchall()
                    for r in rows:
                        if r["amount"] is not None:
                            self.conn.execute("UPDATE journal SET status='VOID' WHERE tx_id=?", (r["tx_id"],))
                            self.conn.execute("UPDATE balance SET current_balance = current_balance + ? WHERE id = 1", (float(r["amount"]),))
                    
                    self.conn.execute("UPDATE journal SET status='MANUAL_CHECK' WHERE status='PRE_COMMIT'")
                    self.conn.execute("COMMIT")
                except:
                    self.conn.execute("ROLLBACK")
                    raise

    def write_panic_file(self, tx_id):
        try:
            with open(os.path.join(DB_DIR, f"{tx_id}.panic"), "w") as f:
                f.write("PLACED")
        except: pass

    def resolve_panics(self):
        import glob
        with self._write_lock:
            with self._lock:
                for p_file in glob.glob(os.path.join(DB_DIR, "*.panic")):
                    tx_id = os.path.basename(p_file).replace(".panic", "")
                    try:
                        self.conn.execute("BEGIN IMMEDIATE")
                        self.conn.execute("UPDATE journal SET status='PLACED' WHERE tx_id=?", (tx_id,))
                        self.conn.execute("COMMIT")
                        os.remove(p_file)
                    except: self.conn.execute("ROLLBACK")

    # 🛡️ Metodo Sicuro per l'Engine
    def mark_manual_check(self, tx_id):
        with self._write_lock:
            with self._lock:
                self.conn.execute("BEGIN IMMEDIATE")
                try:
                    self.conn.execute(
                        "UPDATE journal SET status='MANUAL_CHECK' WHERE tx_id=?",
                        (tx_id,)
                    )
                    self.conn.execute("COMMIT")
                except:
                    self.conn.execute("ROLLBACK")
                    raise

    # 🛡️ Metodo Sicuro per il Money Manager
    def commit(self, tx_id, payout):
        with self._write_lock:
            with self._lock:
                self.conn.execute("BEGIN IMMEDIATE")
                try:
                    row = self.conn.execute(
                        "SELECT amount FROM journal WHERE tx_id=?",
                        (tx_id,)
                    ).fetchone()

                    if not row:
                        raise ValueError("Transazione non trovata")

                    stake = float(row["amount"])
                    profit = float(payout) - stake

                    self.conn.execute(
                        "UPDATE journal SET status='SETTLED', payout=? WHERE tx_id=?",
                        (payout, tx_id)
                    )

                    self.conn.execute(
                        "UPDATE balance SET current_balance = current_balance + ? WHERE id = 1",
                        (profit + stake,)
                    )

                    self.conn.execute(
                        "UPDATE balance SET peak_balance = MAX(peak_balance, current_balance) WHERE id = 1"
                    )

                    self.conn.execute("COMMIT")
                except:
                    self.conn.execute("ROLLBACK")
                    raise