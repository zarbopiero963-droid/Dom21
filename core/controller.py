import os
import sys
import logging
import threading
import time
import sqlite3
import traceback
import psutil
from typing import Dict, Any
from PySide6.QtCore import QObject, Signal

from core.event_bus import bus
from core.playwright_worker import PlaywrightWorker
from core.telegram_worker import TelegramWorker
from core.execution_engine import ExecutionEngine
from core.money_management import MoneyManager
from core.dom_executor_playwright import DomExecutorPlaywright
from core.database import Database
from core.config_loader import ConfigLoader
from core.secure_storage import RobotManager


class SuperAgentController(QObject):
    log_message = Signal(str)
    ai_analysis_ready = Signal(str)

    def __init__(self, logger):
        super().__init__()
        self.logger = logger

        self.config_loader = ConfigLoader()
        self.config = self.config_loader.load_config()
        allow_bets = self.config.get("betting", {}).get("allow_place", False)

        self.db = Database()
        self.money_manager = MoneyManager(self.db)
        
        try:
            pending = self.money_manager.db.pending()
            if pending:
                br_before = self.money_manager.bankroll()
                self.logger.warning(f"🧹 Pulizia Pre-Flight: Rilevate {len(pending)} zombie. Bankroll: €{br_before:.2f}")
                for p in pending:
                    self.money_manager.refund(p["tx_id"])
                br_after = self.money_manager.bankroll()
                self.logger.warning(f"🧹 Rollback completato. Bankroll ripristinato a: €{br_after:.2f}")
        except Exception as e:
            self.logger.error(f"Errore pulizia zombie DB: {e}")

        self._worker_lock = threading.Lock()
        self._restarting = False  # 🔴 FIX 1: Atomicità riavvio
        self.restart_timestamps = [] # 🔴 FIX 4: Restart Storm Prevention

        self.worker = PlaywrightWorker(logger)
        self.worker.executor = DomExecutorPlaywright(
            logger=logger,
            allow_place=allow_bets
        )

        self.engine = ExecutionEngine(bus, self.worker.executor, logger)
        self.telegram = TelegramWorker(self.config)
        self.telegram.message_received.connect(self.process_signal)

        self.is_running = False
        self.last_heartbeat = time.monotonic()  # 🔴 FIX 3: Monotonic safe
        self.engine.betting_enabled = False
        self._bus_started = False

        self.bet_lock = False
        self.circuit_open = False
        self._lock = threading.Lock()

        bus.subscribe("BET_SUCCESS", self._on_bet_success)
        bus.subscribe("BET_FAILED", self._on_bet_failed)

        threading.Thread(target=self._master_watchdog, daemon=True).start()

    def start_listening(self):
        if self.is_running or self.circuit_open:
            self.logger.warning("Motore già attivo o Circuit Breaker APERTO.")
            return

        self.logger.info("🟢 MOTORE AVVIATO")
        self.is_running = True
        self.engine.betting_enabled = True

        if not self._bus_started:
            bus.start()
            self._bus_started = True

        with self._worker_lock:
            if not getattr(self.worker, "running", False):
                self.worker.start()
                self.worker.start_time = time.monotonic()

        if self.telegram and not getattr(self.telegram, "running", False):
            self.telegram.start()

    def stop_listening(self):
        if not self.is_running: return
        self.logger.warning("🔴 STOP MOTORE")
        self.is_running = False
        self.engine.betting_enabled = False
        if self.telegram:
            self.telegram.stop()

    def _load_robots(self):
        return RobotManager().all()

    def _match_robot(self, payload, robot_config):
        text = payload.get("raw_text", "").lower()
        if not text: text = f"{payload.get('teams','')} {payload.get('market','')}".lower()
        triggers = robot_config.get("trigger_words", [])
        if isinstance(triggers, str): triggers = [t.strip() for t in triggers.split(",") if t.strip()]
        excludes = robot_config.get("exclude_words", [])
        if isinstance(excludes, str): excludes = [e.strip() for e in excludes.split(",") if e.strip()]
        for ex in excludes:
            if ex and ex.lower() in text: return False
        if not triggers: return True
        for t in triggers:
            if t.lower() in text: return True
        return False

    def process_signal(self, payload):
        if not self.is_running or self.circuit_open: return False
        
        # 🔴 FIX 2: Prevenzione saturazione coda Worker (Load Shedding)
        if bus._pending > 30:
            self.logger.warning("⚠️ Worker/Bus saturo (>30 task). Signal droppato.")
            return False

        if isinstance(payload, str):
            payload = {"teams": "Auto", "market": "N/A", "raw_text": payload}

        robots = self._load_robots()
        if not robots: return False

        for r in robots:
            if not r.get("is_active", True): continue
            if self._match_robot(payload, r):
                payload["is_active"] = True
                payload["robot_name"] = r.get("name")
                payload["stake"] = r.get("stake", 2.0)
                payload["mm_mode"] = r.get("mm_mode", "Stake Fisso")

                with self._worker_lock:
                    if getattr(self.worker, "running", False):
                        self.worker.submit(self.engine.process_signal, payload, self.money_manager)
                        return True
                    else:
                        self.logger.error("Worker spento durante l'invio del task")
                        return False
        return False

    def handle_signal(self, signal):
        return self.process_signal(signal)

    def _nuclear_restart_worker(self):
        """Uccide il thread del worker zombie e lo rigenera in thread-safety."""
        # 🔴 FIX 1: Flag Atomico contro Race Conditions multiple
        if getattr(self, '_restarting', False): return
        self._restarting = True
        
        try:
            now = time.monotonic()
            # 🔴 FIX 4: Restart Storm Prevention (Max 3 in 5 min)
            self.restart_timestamps = [t for t in self.restart_timestamps if now - t < 300]
            self.restart_timestamps.append(now)
            
            if len(self.restart_timestamps) >= 3:
                self.logger.critical("🛑 RESTART STORM (3 crash in 5m)! Attivazione RISK_OFF GLOBALE.")
                self.circuit_open = True
                self.stop_listening()
                return

            self.logger.critical("☢️ NUCLEAR RESTART: Riavvio forzato del Playwright Worker...")
            with self._worker_lock:
                try:
                    self.worker.stop()
                    time.sleep(2)
                    
                    # 🔴 Kill Zombie Processes Chromium a livello OS
                    for p in psutil.process_iter(['name']):
                        try:
                            n = (p.info['name'] or '').lower()
                            if 'chromium' in n or 'chrome' in n:
                                p.kill()
                        except: pass

                    self.worker = PlaywrightWorker(self.logger)
                    allow_bets = self.config.get("betting", {}).get("allow_place", False)
                    self.worker.executor = DomExecutorPlaywright(logger=self.logger, allow_place=allow_bets)
                    self.engine.executor = self.worker.executor
                    
                    if self.is_running:
                        self.worker.start()
                        self.worker.start_time = time.monotonic()
                        
                    self.logger.info("♻️ Worker rigenerato con successo.")
                except Exception as e:
                    self.logger.error(f"Fallito Nuclear Restart: {e}")
        finally:
            self._restarting = False

    def _on_bet_success(self, event): self.logger.info(f"✅ BET SUCCESS {event}")
    def _on_bet_failed(self, event): self.logger.info(f"❌ BET FAILED {event}")

    def _master_watchdog(self):
        self.logger.info("👁️ Master Watchdog attivo")
        loops_count = 0
        
        while True:
            time.sleep(30)
            loops_count += 1
            self.last_heartbeat = time.monotonic()
            
            try:
                with open("C:/tmp/roserpina_controller_heartbeat" if os.name == 'nt' else "/tmp/roserpina_controller_heartbeat", "w") as f:
                    f.write(str(time.time())) # Qui manteniamo epoch per bash esterno
                    f.flush()
                    os.fsync(f.fileno())
            except Exception: pass

            if not self.is_running: continue

            # 🔴 FIX 8: OS FULL RESTART SU RAM > 900MB
            if loops_count % 2 == 0:
                try:
                    process = psutil.Process(os.getpid())
                    mem_mb = process.memory_info().rss / (1024 * 1024)
                    if mem_mb > 900.0:
                        self.logger.critical(f"💀 FATAL OOM RISK: RAM a {mem_mb:.1f}MB. FULL OS RESTART RICHIESTO.")
                        os._exit(1) # systemd/nssm lo resusciterà da zero
                except Exception: pass

            if self.telegram and not getattr(self.telegram, "running", False):
                self.logger.critical("📡 Telegram Zombie. Riavvio...")
                try: self.telegram.stop()
                except: pass
                time.sleep(1)
                try: self.telegram.start()
                except: pass

            if hasattr(self.worker, 'last_worker_heartbeat'):
                elapsed_heartbeat = time.monotonic() - self.worker.last_worker_heartbeat
                if elapsed_heartbeat > 120:
                    worker_uptime = time.monotonic() - getattr(self.worker, "start_time", time.monotonic())
                    if worker_uptime >= 60:
                        self.logger.critical(f"💀 WORKER FREEZE DETECTED ({elapsed_heartbeat:.0f}s).")
                        self._nuclear_restart_worker()

            if loops_count % 4 == 0:
                try:
                    if self.money_manager.db.pending():
                        with self._worker_lock:
                            if getattr(self.worker, "running", False):
                                def check_job():
                                    try:
                                        fresh = self.money_manager.db.pending()
                                        if not fresh: return
                                        res = self.worker.executor.check_settled_bets()
                                        if not res or not res.get("status"): return
                                        s, p, tx = res["status"], res.get("payout", 0.0), fresh[0]["tx_id"]
                                        if s == "WIN": self.money_manager.win(tx, p)
                                        elif s == "LOSS": self.money_manager.loss(tx)
                                        elif s == "VOID": self.money_manager.refund(tx)
                                    except Exception: pass
                                self.worker.submit(check_job)
                except sqlite3.OperationalError as e:
                    if "database is locked" in str(e).lower():
                        try:
                            self.db.close()
                            self.db = Database()
                            self.money_manager.db = self.db
                        except Exception: pass

            if loops_count % 20 == 0:
                if not self.money_manager.db.pending():
                    with self._worker_lock:
                        if getattr(self.worker, "running", False):
                            def reconcile_job():
                                try:
                                    bal = self.worker.executor.get_balance()
                                    if bal is not None: self.money_manager.reconcile_balances(bal)
                                except Exception: pass
                            self.worker.submit(reconcile_job)

            if loops_count >= 240:
                loops_count = 0  
                try:
                    self.db.maintain_wal() # 🔴 FIX 6.2: Check dim. WAL
                    if not self.money_manager.db.pending():
                        self.db.conn.execute("VACUUM")
                except Exception: pass
