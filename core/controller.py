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
        
        # 🚑 PANIC LEDGER RECOVERY
        try:
            self.db.resolve_panics()
        except Exception as e:
            self.logger.error(f"Panic Ledger Recovery fallito: {e}")

        # 🔒 Crash Recovery 2-Phase
        try:
            self.db.recover_reserved()
            self.logger.info("🧹 Boot Recovery: Cleaned up orphaned RESERVED transactions.")
        except Exception as e:
            self.logger.error(f"Recovery RESERVED fallita: {e}")

        # 🔴 RECOVERY BET PLACED NON CHIUSE
        try:
            placed = self.db.get_unsettled_placed()
            if placed:
                self.logger.critical(f"♻️ RECOVERY: Trovate {len(placed)} PLACED post-crash.")
                self.logger.critical("⚠️ LE SCOMMESSE RESTANO PLACED: Sarà il check_settled_bets a verificare l'esito reale.")
        except Exception as e:
            self.logger.error(f"Placed recovery error: {e}")

        self.money_manager = MoneyManager(self.db)
        
        self._worker_lock = threading.Lock()
        self._restarting = False
        self.restart_timestamps = []

        self.worker = PlaywrightWorker(logger)
        self.worker.executor = DomExecutorPlaywright(
            logger=logger,
            allow_place=allow_bets
        )

        self.engine = ExecutionEngine(bus, self.worker.executor, logger)
        self.telegram = TelegramWorker(self.config)
        self.telegram.message_received.connect(self.process_signal)

        self.is_running = False
        self.last_heartbeat = time.monotonic()
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

    def stop(self):
        self.logger.warning("🔴 STOP CONTROLLER: Inizio sequenza di spegnimento.")
        self.is_running = False 
        
        # 🛡️ 1. Drenaggio Worker: Svuota la coda e completa le task IN VOLO.
        # Spostato PRIMA dell'Engine.
        if hasattr(self, "worker") and self.worker:
            self.logger.info("Arresto Playwright Worker (Drain Coda)...")
            try:
                self.worker.stop()
            except Exception:
                pass

        # 🛡️ 2. Blocco Engine: Ora che la coda è vuota e i click sono finiti,
        # sigilliamo definitivamente l'engine (Barrier Check finale).
        if hasattr(self, "engine"):
            self.engine.stop_engine()
            
        if hasattr(self, "telegram") and self.telegram:
            try:
                self.telegram.stop()
            except Exception:
                pass
                
        self.logger.info("🛑 Motore transazionale disconnesso con successo.")

    def stop_listening(self):
        self.stop()

    def _load_robots(self):
        return RobotManager().all()

    def _match_robot(self, payload, robot_config):
        text = payload.get("raw_text", "").lower()
        if not text: text = f"{payload.get('teams','')}".lower()
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
        if getattr(self, '_restarting', False): return
        self._restarting = True
        
        try:
            now = time.monotonic()
            self.restart_timestamps = [t for t in self.restart_timestamps if now - t < 300]
            self.restart_timestamps.append(now)
            
            if len(self.restart_timestamps) >= 3:
                self.logger.critical("🛑 RESTART STORM (3 crash in 5m)! Attivazione RISK_OFF GLOBALE.")
                self.circuit_open = True
                self.stop()
                return

            self.logger.critical("☢️ NUCLEAR RESTART: Riavvio forzato del Playwright Worker...")
            with self._worker_lock:
                try:
                    self.worker.stop()
                    time.sleep(2)
                    
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
                except Exception as ex:
                    self.logger.critical(f"Errore durante NUCLEAR RESTART: {ex}")
        finally:
            self._restarting = False

    def _master_watchdog(self):
        self.logger.info("👁️ Master Watchdog attivo")
        while True:
            time.sleep(30)
            if not self.is_running: continue

            # 1. Thread del Worker
            if self.worker:
                is_dead = False
                if hasattr(self.worker, 'running'):
                    is_dead = not self.worker.running

                if is_dead:
                    self.logger.critical("📡 Worker Thread morto silenziosamente. Innesco riavvio...")
                    self._nuclear_restart_worker()
            
            # 🛡️ FIX WATCHDOG CRASH: Compatibilità PyQt/PySide per i QThread
            if self.telegram:
                is_dead = False
                if hasattr(self.telegram, 'isRunning') and callable(self.telegram.isRunning):
                    is_dead = not self.telegram.isRunning()
                elif hasattr(self.telegram, 'running'):
                    is_dead = not self.telegram.running
                    
                if is_dead:
                    self.logger.error("📡 Telegram Zombie. Riavvio...")
                    try:
                        self.telegram.stop()
                        time.sleep(2)
                        self.telegram.start()
                    except Exception as e:
                        self.logger.critical(f"Fallito riavvio Telegram: {e}")

    def _on_bet_success(self, payload):
        tx_id = payload.get("tx_id", "UNKNOWN")
        stake = payload.get("stake", 0)
        self.log_message.emit(f"✅ BET SUCCESS (Tx: {tx_id}) - {stake}€")

    def _on_bet_failed(self, payload):
        tx_id = payload.get("tx_id", "UNKNOWN")
        reason = payload.get("reason", "Unknown Error")
        self.log_message.emit(f"❌ BET FAILED (Tx: {tx_id}) - Reason: {reason}")
