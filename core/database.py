import os
import time
import threading
import sqlite3
import math
from pathlib import Path
from core.invariants_guard import LedgerGuard

DB_DIR = os.path.join(str(Path.home()), ".superagent_data")
os.makedirs(DB_DIR, exist_ok=True)
DB_PATH = os.path.join(DB_DIR, "money_db.sqlite")

class Database:
    def __init__(self):
        self.conn = sqlite3.connect(DB_PATH, check_same_thread=False, timeout=30, isolation_level=None)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA journal_mode=WAL;")
        self.conn.execute("PRAGMA synchronous=FULL;")
        self.conn.execute("PRAGMA foreign_keys=ON;")
        self.conn.execute("PRAGMA trusted_schema=OFF;")
        
        self._lock = threading.RLock()
        self._write_lock = threading.Lock()
        self._init_db()

    def _init_db(self):
        with self._write_lock:
            with self._lock:
                self.conn.execute("""
                    CREATE TABLE IF NOT EXISTS journal (
                        id INTEGER PRIMARY KEY AUTOINCREMENT, 
                        tx_id TEXT UNIQUE NOT NULL, 
                        amount REAL CHECK(amount > 0), 
                        status TEXT NOT NULL, 
                        payout REAL DEFAULT 0 CHECK(payout >= 0), 
                        timestamp INTEGER, 
                        table_id INTEGER DEFAULT 1, 
                        teams TEXT DEFAULT '',
                        match_hash TEXT DEFAULT ''
                    )
                """)
                self.conn.execute("""
                    CREATE TABLE IF NOT EXISTS balance (
                        id INTEGER PRIMARY KEY CHECK (id = 1), 
                        current_balance REAL CHECK (current_balance >= 0), 
                        peak_balance REAL CHECK (peak_balance >= current_balance)
                    )
                """)
                self.conn.execute("INSERT OR IGNORE INTO balance (id, current_balance, peak_balance) VALUES (1, 1000.0, 1000.0)")
                self.conn.execute("""
                    CREATE TRIGGER IF NOT EXISTS enforce_peak_monotonic
                    BEFORE UPDATE ON balance
                    FOR EACH ROW
                    WHEN NEW.peak_balance < OLD.peak_balance
                    BEGIN
                        SELECT RAISE(ABORT, 'FATAL INVARIANT: Peak balance cannot decrease');
                    END;
                """)

    def get_balance(self):
        with self._lock:
            row = self.conn.execute("SELECT current_balance, peak_balance FROM balance WHERE id = 1").fetchone()
            return (float(row["current_balance"]), float(row["peak_balance"])) if row else (0.0, 0.0)

    # 🛡️ FIX 2: Metodo legacy reintrodotto con Hard Constraints C-Level
    def update_bankroll(self, current_balance, peak_balance):