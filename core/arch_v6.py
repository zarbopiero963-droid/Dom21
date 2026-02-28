import threading
import queue
import time
import concurrent.futures
import os
import signal

# Constants
JOIN_TIMEOUT = 2
HEALTH_CHECK_INTERVAL = 15
WATCHDOG_INTERVAL = 20


# --- 1. CENTRAL EVENT BUS ---
class EventBusV6:
    """Pub/Sub with single dispatcher thread and backpressure to prevent RAM explosion."""

    def __init__(self, logger):
        self.logger = logger
        self.listeners = {}
        self.lock = threading.Lock()
        self._queue = queue.Queue(maxsize=5000)
        self._running = True
        self._dispatcher = threading.Thread(
            target=self._dispatch_loop, daemon=True, name="EventBus_Dispatcher"
        )
        self._dispatcher.start()

    def subscribe(self, event, fn):
        with self.lock:
            if event not in self.listeners:
                self.listeners[event] = []
            self.listeners[event].append(fn)

    def emit(self, event, data=None):
        try:
            self._queue.put_nowait((event, data))
        except queue.Full:
            self.logger.critical(f"⚠️ EventBus SATURATO (>5000 in coda). Dropping event: {event}")

    def _dispatch_loop(self):
        while self._running:
            try:
                event, data = self._queue.get(timeout=1)
            except queue.Empty:
                continue
                
            with self.lock:
                listeners = list(self.listeners.get(event, []))
                
            for fn in listeners:
                try:
                    fn(data)
                except Exception as e:
                    self.logger.error(f"EventBus Error ({event}): {e}")
                    
            self._queue.task_done()

    def stop(self):
        self._running = False
        # 🛡️ FIX GRACEFUL SHUTDOWN: Drena e chiude senza tagliare processi in corso
        while not self._queue.empty():
            try:
                self._queue.get_nowait()
                self._queue.task_done()
            except queue.Empty:
                break
        try:
            self._dispatcher.join(timeout=JOIN_TIMEOUT)
        except Exception:
            pass


# --- 2. PLAYWRIGHT WORKER (Anti-Freeze & IPC Timeout Protection) ---
class PlaywrightWorker:
    def __init__(self, executor, logger):
        self.executor = executor
        self.logger = logger
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
                
                # Sentinel per il Graceful Shutdown
                if fn is None:
                    self.queue.task_done()
                    break
                
                try:
                    # 🛡️ GOD MODE: Esecuzione segregata con timeout assoluto contro il freeze IPC
                    future = self._pool.submit(fn, *args, **kwargs)
                    future.result(timeout=90.0)
                except concurrent.futures.TimeoutError:
                    self.logger.critical("💀 WORKER TIMEOUT: Playwright bloccato o in freeze. Abortisco task.")
                    self._restart_pool()
                except Exception as e:
                    self.logger.error(f"Worker Task Error: {e}")
                finally:
                    # Garantisce il decremento del task counter per la barriera di drain
                    self.queue.task_done()
                    
            except queue.Empty:
                continue

    def stop(self):
        self.running = False
        
        # 1. Inietta Sentinel per sbloccare la coda istantaneamente
        self.queue.put((None, None, None))
        
        # 2. Barriera di Drain: attende che tutti i task precedenti e la sentinel siano processati
        self.logger.info("⏳ PlaywrightWorker: Drenaggio coda in corso...")
        self.queue.join()
        
        # 3. Thread Join: chiusura elegante del ciclo
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=JOIN_TIMEOUT)
            
        # 4. Pool Shutdown transazionale
        if self._pool:
            self._pool.shutdown(wait=True)
            
        self.logger.info("🛑 PlaywrightWorker: Shutdown completato.")


# --- 3. SESSION GUARDIAN (Auto-Recovery) ---
class SessionGuardian:
    MAX_FAILURES = 3

    def __init__(self, executor, logger):
        self.executor = executor
        self.logger = logger
        self.stop_event = threading.Event()
        self._consecutive_failures = 0

    def start(self):
        threading.Thread(target=self._loop, daemon=True, name="SessionGuardian").start()

    def _loop(self):
        self.logger.info(
            f"Session Guardian active (check every {HEALTH_CHECK_INTERVAL}s, "
            f"recovery after {self.MAX_FAILURES} fails)."
        )
        while not self.stop_event.wait(HEALTH_CHECK_INTERVAL):
            try:
                if not self.executor.check_health():
                    self._consecutive_failures += 1
                    self.logger.warning(
                        f"Browser unhealthy ({self._consecutive_failures}/{self.MAX_FAILURES})"
                    )
                    if self._consecutive_failures >= self.MAX_FAILURES:
                        self._do_recovery()
                        self._consecutive_failures = 0
                else:
                    if self._consecutive_failures > 0:
                        self.logger.info("Browser back to healthy.")
                    self._consecutive_failures = 0
            except Exception as e:
                self.logger.error(f"Guardian Error: {e}")

    def _do_recovery(self):
        self.logger.warning("Automatic recovery in progress...")
        try:
            if hasattr(self.executor, "recover_session"):
                success = self.executor.recover_session()
            elif (
                hasattr(self.executor, "recycle_browser")
                and not getattr(self.executor, "is_attached", False)
            ):
                success = self.executor.recycle_browser()
            else:
                self.logger.error("Automatic recovery not possible with current config.")
                return

            if success:
                self.logger.info("Recovery completed successfully.")
            else:
                self.logger.error("Recovery attempt failed.")
        except Exception as e:
            self.logger.error(f"Recovery process crashed: {e}", exc_info=True)

    def stop(self):
        self.stop_event.set()


# --- 4. PLAYWRIGHT WATCHDOG (Thread Monitor) ---
class PlaywrightWatchdog:
    def __init__(self, worker, logger):
        self.worker = worker
        self.logger = logger
        self.stop_event = threading.Event()
        self._restart_lock = threading.Lock()

    def start(self):
        threading.Thread(target=self._loop, daemon=True, name="PW_Watchdog").start()

    def _loop(self):
        while not self.stop_event.wait(WATCHDOG_INTERVAL):
            # 🛡️ FIX WATCHDOG: Guard su NoneType thread
            if self.worker.running and self.worker.thread and not self.worker.thread.is_alive():
                self.logger.critical("ALERT: Playwright Worker thread is dead! Restarting...")
                self._restart_worker()

    def _restart_worker(self):
        with self._restart_lock:
            try:
                if self.worker.thread and self.worker.thread.is_alive():
                    return
                self.worker.thread = threading.Thread(
                    target=self.worker._loop, daemon=True, name="PW_Worker"
                )
                self.worker.thread.start()
                self.logger.info("Playwright Worker restarted by Watchdog.")
            except Exception as e:
                self.logger.error(f"Watchdog: cannot restart Worker: {e}")

    def stop(self):
        self.stop_event.set()