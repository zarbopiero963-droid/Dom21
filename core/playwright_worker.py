import threading
import queue
import traceback
import logging
import time
import concurrent.futures
import os
import signal

class PlaywrightWorker:
    def __init__(self, logger=None):
        self.logger = logger or logging.getLogger("PlaywrightWorker")
        self.q = queue.Queue()
        self.running = False
        self.thread = None
        self.executor = None
        
        self._pool = concurrent.futures.ThreadPoolExecutor(max_workers=1)
        self.last_worker_heartbeat = time.time()

    def start(self):
        self.running = True
        if self._pool is None:
            self._pool = concurrent.futures.ThreadPoolExecutor(max_workers=1)
        self.thread = threading.Thread(target=self._run, daemon=False)
        self.thread.start()
        self.last_worker_heartbeat = time.time()
        self.logger.info("Playwright Worker avviato.")

    def stop(self):
        self.logger.info("Arresto Playwright Worker richiesto...")
        self.running = False
        
        self.q.put((None, None, None))
        
        if self.thread:
            self.logger.info("Attendiamo lo svuotamento della coda e la fine delle scommesse...")
            self.thread.join()
            
        if self._pool:
            self.logger.info("Chiusura ThreadPool...")
            self._pool.shutdown(wait=True)
            
        self.logger.info("Playwright Worker arrestato in sicurezza e senza troncamenti.")

    def submit(self, func, *args, **kwargs):
        if self.running:
            self.q.put((func, args, kwargs))

    def is_alive(self):
        return self.thread and self.thread.is_alive()
        
    def _restart_pool(self):
        self.logger.warning("♻️ Ricreazione ThreadPoolExecutor causa Timeout...")
        if self._pool:
            self._pool.shutdown(wait=False)
        self._pool = concurrent.futures.ThreadPoolExecutor(max_workers=1)
        
        active_threads = threading.active_count()
        self.logger.warning(f"Thread attivi nel sistema: {active_threads}")
        
        # 🛡️ FIX ZOMBIE LEAK: Hard reset OS se i thread accumulati rischiano di saturare la RAM
        if active_threads > 20:
            self.logger.critical("💀 FATAL LEAK: Troppi thread zombie. OS Watchdog Trigger!")
            self.logger.critical("Eseguo SIGTERM su me stesso per pulizia profonda via Supervisor/Systemd.")
            os.kill(os.getpid(), signal.SIGTERM)

    def _run(self):
        self.logger.info("Worker Loop Iniziato.")
        
        while True: 
            self.last_worker_heartbeat = time.time()
            
            try:
                task = self.q.get(timeout=1.0)
                func, args, kwargs = task
                
                if func is None:
                    self.q.task_done()
                    break 
                
                try:
                    self.last_worker_heartbeat = time.time()
                    future = self._pool.submit(func, *args, **kwargs)
                    future.result(timeout=90.0)
                    
                except concurrent.futures.TimeoutError:
                    self.logger.critical("💀 WORKER TIMEOUT: Job bloccato >90s. Playwright in freeze IPC!")
                    self._restart_pool()
                    
                    self.last_worker_heartbeat = time.time()
                    self.q.task_done()
                    continue
                    
                except Exception as e:
                    self.logger.error(f"❌ Worker Task Crash: {e}\n{traceback.format_exc()}")
                    
                    self.last_worker_heartbeat = time.time()
                    self.q.task_done()
                    continue
                    
                self.last_worker_heartbeat = time.time()
                self.q.task_done()
                    
            except queue.Empty:
                if not self.running:
                    break 
                continue
            except Exception as e:
                self.logger.error(f"Errore critico nella coda worker: {e}")
                
        self.logger.info("Worker Loop Terminato in sicurezza.")