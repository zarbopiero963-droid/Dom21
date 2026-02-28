import threading
import queue
import time

class EventBusV6:
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

    @property
    def pending_count(self):
        return self._queue.qsize()

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
        while not self._queue.empty():
            try:
                self._queue.get_nowait()
                self._queue.task_done()
            except queue.Empty:
                break
        try:
            self._dispatcher.join(timeout=2)
        except Exception:
            pass

import logging
bus = EventBusV6(logging.getLogger("DummyBus"))