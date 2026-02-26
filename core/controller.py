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
        
        # 🔒 Crash Recovery 2-Phase (Bootloader)
        try:
            self.db.recover_reserved()
            self.logger.info("🧹 Boot Recovery: Cleaned up orphaned RESERVED transactions.")
        except Exception as e:
            self.logger.error(f"Recovery RESERVED fallita: {e}")

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

# ... (Il resto di controller.py rimane invariato)
