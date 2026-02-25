import sqlite3
import os
import time
import logging
import threading
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
        self.conn.execute("PRAGMA busy_timeout=5000;")
        self._lock = threading.RLock()
        self._init_db()

    def _init_db(self):
        with self._lock:
            self.conn.execute("CREATE TABLE IF NOT EXISTS journal (id INTEGER PRIMARY KEY AUTOINCREMENT, tx_id TEXT UNIQUE, amount REAL, status TEXT, payout REAL DEFAULT 0, timestamp INTEGER, table_id INTEGER DEFAULT 1, teams TEXT DEFAULT '')")
            # 🔴 FIX 6.1: Indici per prevenire timeout letali dopo mesi di utilizzo
            self.conn.execute("CREATE INDEX IF NOT EXISTS idx_status ON journal(status);")
            self.conn.execute("CREATE INDEX IF NOT EXISTS idx_ts ON journal(timestamp);")

            try: self.conn.execute("ALTER TABLE journal ADD COLUMN table_id INTEGER DEFAULT 1")
            except: pass
            try: self.conn.execute("ALTER TABLE journal ADD COLUMN teams TEXT DEFAULT ''")
            except: pass

            self.conn.execute("CREATE TABLE IF NOT EXISTS balance (id INTEGER PRIMARY KEY CHECK (id = 1), current_balance REAL, peak_balance REAL DEFAULT 1000.0)")
            self.conn.execute("INSERT OR IGNORE INTO balance (id, current_balance, peak_balance) VALUES (1, 1000.0, 1000.0)")
            self.conn.execute("CREATE TABLE IF NOT EXISTS roserpina_tables (table_id INTEGER PRIMARY KEY, profit REAL DEFAULT 0.0, loss REAL DEFAULT 0.0, in_recovery INTEGER DEFAULT 0)")
            for i in range(1, 6): self.conn.execute("INSERT OR IGNORE INTO roserpina_tables (table_id) VALUES (?)", (i,))

    def maintain_wal(self):
        """🔴 FIX 6.2: Prevenzione corruzione da file WAL gigante"""
        wal_path = DB_PATH + "-wal"
        if os.path.exists(wal_path) and os.path.getsize(wal_path) > 50 * 1024 * 1024:
            try: self.conn.execute("PRAGMA wal_checkpoint(TRUNCATE);")
            except: pass

    def get_balance(self):
        with self._lock:
            row = self.conn.execute("SELECT current_balance, peak_balance FROM balance WHERE id = 1").fetchone()
            return (float(row["current_balance"]), float(row["peak_balance"])) if row else (0.0, 0.0)

    def update_bankroll(self, amount):
        with self._lock:
            self.conn.execute("BEGIN IMMEDIATE")
            try:
                self.conn.execute("UPDATE balance SET current_balance = ?, peak_balance = MAX(peak_balance, ?) WHERE id = 1", (float(amount), float(amount)))
                self.conn.execute("COMMIT")
            except: self.conn.execute("ROLLBACK"); raise

    def reserve(self, tx_id, amount, table_id=1, teams=""):
        with self._lock:
            self.conn.execute("BEGIN IMMEDIATE")
            try:
                self.conn.execute("INSERT INTO journal (tx_id, amount, status, timestamp, table_id, teams) VALUES (?, ?, 'PENDING', ?, ?, ?)", (tx_id, float(amount), int(time.time()), table_id, teams))
                self.conn.execute("UPDATE balance SET current_balance = current_balance - ? WHERE id = 1", (float(amount),))
                self.conn.execute("COMMIT")
            except: self.conn.execute("ROLLBACK"); raise

    def commit(self, tx_id, payout):
        with self._lock:
            self.conn.execute("BEGIN IMMEDIATE")
            try:
                self.conn.execute("UPDATE journal SET status = 'SETTLED', payout = ? WHERE tx_id = ?", (float(payout), tx_id))
                if float(payout) > 0: self.conn.execute("UPDATE balance SET peak_balance = MAX(peak_balance, current_balance + ?), current_balance = current_balance + ? WHERE id = 1", (float(payout), float(payout)))
                self.conn.execute("COMMIT")
            except: self.conn.execute("ROLLBACK"); raise

    def rollback(self, tx_id):
        with self._lock:
            self.conn.execute("BEGIN IMMEDIATE")
            try:
                row = self.conn.execute("SELECT amount FROM journal WHERE tx_id = ? AND status = 'PENDING'", (tx_id,)).fetchone()
                if row:
                    self.conn.execute("UPDATE journal SET status = 'VOID' WHERE tx_id = ?", (tx_id,))
                    self.conn.execute("UPDATE balance SET current_balance = current_balance + ? WHERE id = 1", (float(row["amount"]),))
                self.conn.execute("COMMIT")
            except: self.conn.execute("ROLLBACK"); raise

    def pending(self):
        with self._lock: return [dict(r) for r in self.conn.execute("SELECT * FROM journal WHERE status = 'PENDING' ORDER BY timestamp ASC").fetchall()]

    def get_roserpina_tables(self):
        with self._lock: return [dict(r) for r in self.conn.execute("SELECT * FROM roserpina_tables ORDER BY table_id ASC").fetchall()]

    def update_roserpina_table(self, table_id, profit_delta, loss_delta, in_recovery):
        with self._lock:
            self.conn.execute("BEGIN IMMEDIATE")
            try:
                self.conn.execute("UPDATE roserpina_tables SET profit = profit + ?, loss = loss + ?, in_recovery = ? WHERE table_id = ?", (float(profit_delta), float(loss_delta), int(in_recovery), table_id))
                self.conn.execute("COMMIT")
            except: self.conn.execute("ROLLBACK"); raise

    def close(self):
        try: self.conn.close()
        except: pass
