import threading
import queue
import concurrent.futures
import os
import signal

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
        if self._pool is None: self._pool = concurrent.futures.ThreadPoolExecutor(max_workers=1)
        self.thread = threading.Thread(target=self._loop, daemon=True, name="PW_Worker")
        self.thread.start()

    def submit(self, fn, *args, **kwargs):
        if self.running: self.queue.put((fn, args, kwargs))

    def _restart_pool(self):
        if self._pool: self._pool.shutdown(wait=False)
        self._pool = concurrent.futures.ThreadPoolExecutor(max_workers=1)
        if threading.active_count() > 20:
            os.kill(os.getpid(), signal.SIGTERM)

    def _loop(self):
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
                    self._restart_pool()
                except Exception: pass
                finally: self.queue.task_done()
            except queue.Empty: continue

    def stop(self):
        self.running = False
        self.queue.put((None, None, None))
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=30.0)
        if self._pool: self._pool.shutdown(wait=False)