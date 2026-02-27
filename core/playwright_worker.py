import threading
import queue
import traceback
import logging
import time
import concurrent.futures

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
        
        # 🛡️ FIX 1: Mai usare daemon=True per thread transazionali. 
        # Garantisce l'esecuzione dei blocchi 'finally' alla chiusura del processo.
        self.thread = threading.Thread(target=self._run, daemon=False)
        self.thread.start()
        
        self.last_worker_heartbeat = time.time()
        self.logger.info("Playwright Worker avviato.")

    def stop(self):
        self.logger.info("Arresto Playwright Worker richiesto...")
        self.running = False
        
        # Inseriamo la Poison Pill per sbloccare la queue in modo pulito
        self.q.put((None, None, None))
        
        if self._pool:
            # 🛡️ FIX 2: wait=True obbliga il ThreadPool ad aspettare la fine della transazione
            # in corso prima di chiudere la serranda.
            self.logger.info("Attendiamo lo svuotamento del ThreadPool...")
            self._pool.shutdown(wait=True)
            
        if self.thread:
            # 🛡️ FIX 3: Niente timeout aggressivi. Join assoluto per garantire la sincronizzazione.
            self.logger.info("Attendiamo la chiusura del Worker Loop...")
            self.thread.join()
            
        self.logger.info("Playwright Worker arrestato in sicurezza e senza troncamenti.")

    def submit(self, func, *args, **kwargs):
        if self.running:
            self.q.put((func, args, kwargs))

    def is_alive(self):
        return self.thread and self.thread.is_alive()
        
    def _restart_pool(self):
        """Abbandona il thread zombie e ricrea il pool."""
        self.logger.warning("♻️ Ricreazione ThreadPoolExecutor causa Timeout...")
        if self._pool:
            self._pool.shutdown(wait=False)
        self._pool = concurrent.futures.ThreadPoolExecutor(max_workers=1)
        
        # Tracciamento Thread Zombie (Prevenzione OOM su VPS)
        active_threads = threading.active_count()
        self.logger.warning(f"Thread attivi nel sistema: {active_threads}")
        
        if active_threads > 15:
            self.logger.critical("⚠️ ALLARME LEAK: Troppi thread zombie accumulati.")
            self.logger.critical("Il sistema è degradato. Richiesto intervento del Watchdog OS (Restart PID).")

    def _run(self):
        self.logger.info("Worker Loop Iniziato.")
        
        while True: 
            self.last_worker_heartbeat = time.time()
            
            try:
                task = self.q.get(timeout=1.0)
                func, args, kwargs = task
                
                if func is None:
                    # Poison Pill ricevuta. Uscita sicura.
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
                    
                # Esecuzione completata con successo
                self.last_worker_heartbeat = time.time()
                self.q.task_done()
                    
            except queue.Empty:
                # 🛡️ FIX 4: Uscita controllata solo se la running condition è False
                if not self.running:
                    break 
                continue
            except Exception as e:
                self.logger.error(f"Errore critico nella coda worker: {e}")
                
        self.logger.info("Worker Loop Terminato in sicurezza.")
