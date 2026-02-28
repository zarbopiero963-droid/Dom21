import threading
import queue
import concurrent.futures
import os
import signal
import traceback
import logging

class PlaywrightWorker:
    # 🛡️ FIX: Costruttore backward-compatible per non rompere Controller e Tester
    def __init__(self, executor, logger=None):
        self.executor = executor
        self.logger = logger or logging.getLogger("PlaywrightWorker")
        self.queue = queue.Queue()
        self.running = True
        self.thread = None
        self._pool = concurrent.futures.ThreadPoolExecutor(max_workers=1)
        self.start()

    def start(self):
        if self._pool is None:
            self._pool = concurrent.futures.ThreadPoolExecutor(max_workers=1)
        self.thread = threading.Thread(target=self._loop, daemon=True, name="PW_Worker")
        self.thread.start()

    def submit(self, fn, *args, **kwargs):
        if self.running:
            self.queue.put((fn, args, kwargs))

    def _restart_pool(self):
        self.logger.warning("♻️ Ricreazione ThreadPoolExecutor causa Timeout IPC...")
        if self._pool:
            self._pool.shutdown(wait=False)
        self._pool = concurrent.futures.ThreadPoolExecutor(max_workers=1)
        
        active_threads = threading.active_count()
        if active_threads > 20:
            self.logger.critical("💀 FATAL LEAK: Troppi thread zombie. OS Watchdog Trigger!")
            os.kill(os.getpid(), signal.SIGTERM)

    def _loop(self):
        self.logger.info("Playwright Worker started.")
        while self.running:
            try:
                task = self.queue.get(timeout=1.0)
                fn, args, kwargs = task
                
                if fn is None:
                    self.queue.task_done()
                    break
                
                try:
                    future = self._pool.submit(fn, *args, **kwargs)
                    future.result(timeout=90.0)
                except concurrent.futures.TimeoutError:
                    self.logger.critical("💀 WORKER TIMEOUT: Playwright bloccato o in freeze. Abortisco task.")
                    self._restart_pool()
                except Exception as e:
                    self.logger.error(f"Worker Task Error: {e}\n{traceback.format_exc()}")
                finally:
                    self.queue.task_done()
                    
            except queue.Empty:
                continue

    def stop(self):
        self.running = False
        self.queue.put((None, None, None))
        self.logger.info("⏳ PlaywrightWorker: Drenaggio coda in corso...")
        
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=30.0)
            if self.thread.is_alive():
                self.logger.critical("💀 Worker thread in deadlock profondo. Forzatura chiusura in corso.")
            
        if self._pool:
            self._pool.shutdown(wait=False)
            
        self.logger.info("🛑 PlaywrightWorker: Shutdown completato.")