import os
import time
import logging
import threading
import sqlite3
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

    def reserve(self, tx_id, amount, table_id=1, teams="", match_hash=""):
        with self._write_lock:
            with self._lock:
                self.conn.execute("BEGIN IMMEDIATE")
                try:
                    self.conn.execute("""
                        INSERT INTO journal (tx_id, amount, status, timestamp, table_id, teams, match_hash)
                        VALUES (?, ?, 'RESERVED', ?, ?, ?, ?)
                    """, (tx_id, float(amount), int(time.time()), table_id, teams, match_hash))
                    self.conn.execute("UPDATE balance SET current_balance = current_balance - ? WHERE id = 1", (float(amount),))
                    self.conn.execute("COMMIT")
                except:
                    self.conn.execute("ROLLBACK")
                    raise

    def mark_pre_commit(self, tx_id):
        """Fase 1.5: Write-Ahead Log dell'intento di click."""
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
        """Ritorna tutte le transazioni in corso (RESERVED, PRE_COMMIT, PLACED, MANUAL_CHECK)."""
        with self._lock:
            return [dict(r) for r in self.conn.execute("SELECT * FROM journal WHERE status NOT IN ('VOID', 'SETTLED')").fetchall()]

    def get_unsettled_placed(self):
        """Ritorna le transazioni PLACED non ancora SETTLED (richiesto dal Controller)."""
        with self._lock:
            return [dict(r) for r in self.conn.execute("SELECT * FROM journal WHERE status='PLACED'").fetchall()]

    def rollback(self, tx_id):
        """Annulla solo se in stato RESERVED."""
        with self._write_lock:
            with self._lock:
                self.conn.execute("BEGIN IMMEDIATE")
                try:
                    row = self.conn.execute("SELECT amount FROM journal WHERE tx_id = ? AND status = 'RESERVED'", (tx_id,)).fetchone()
                    if row:
                        self.conn.execute("UPDATE journal SET status = 'VOID' WHERE tx_id = ?", (tx_id,))
                        self.conn.execute("UPDATE balance SET current_balance = current_balance + ? WHERE id = 1", (float(row["amount"]),))
                    self.conn.execute("COMMIT")
                except:
                    self.conn.execute("ROLLBACK")
                    raise

    def recover_reserved(self):
        """Boot Recovery differenziato."""
        with self._write_lock:
            with self._lock:
                self.conn.execute("BEGIN IMMEDIATE")
                try:
                    # 1. RESERVED -> Refund sicuro
                    rows = self.conn.execute("SELECT tx_id, amount FROM journal WHERE status='RESERVED'").fetchall()
                    for r in rows:
                        self.conn.execute("UPDATE journal SET status='VOID' WHERE tx_id=?", (r["tx_id"],))
                        self.conn.execute("UPDATE balance SET current_balance = current_balance + ? WHERE id = 1", (float(r["amount"]),))
                    
                    # 2. PRE_COMMIT -> Zona d'ombra (MANUAL_CHECK)
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
