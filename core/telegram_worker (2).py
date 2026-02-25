import os
import time
import asyncio
import logging
from queue import Full
from pathlib import Path
try:
    from PySide6.QtCore import QThread, Signal
except ImportError:
    class QThread: pass
    class Signal:
        def __init__(self, *args, **kwargs): pass
        def emit(self, *args, **kwargs): pass
from telethon import TelegramClient, events
from telethon.sessions import StringSession

logger = logging.getLogger("SuperAgent")

class TelegramWorker(QThread):
    message_received = Signal(str)
    status_changed = Signal(str)
    error_occurred = Signal(str)

    def __init__(self, config, message_queue=None):
        super().__init__()
        self.message_queue = message_queue
        self.client = self.loop = self.keep_alive_task = None
        self.running = False
        self.last_heartbeat = time.monotonic()
        self.api_id = int(config.get('telegram', {}).get('api_id', 0) or 0)
        self.api_hash = config.get('telegram', {}).get('api_hash', '')
        raw_chats = config.get('selected_chats', [])
        self.selected_chats = [raw_chats] if isinstance(raw_chats, str) else raw_chats

    def run(self):
        if not self.api_id or not self.api_hash: return
        self.running = True
        self.last_heartbeat = time.monotonic()
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        try: self.loop.run_until_complete(self._main())
        except Exception as e: self.error_occurred.emit(str(e))
        finally:
            self.running = False
            try:
                for task in asyncio.all_tasks(loop=self.loop): task.cancel()
                if not self.loop.is_closed(): self.loop.close()
            except: pass

    async def _main(self):
        save_dir = os.path.join(str(Path.home()), ".superagent_data")
        session_file = os.path.join(save_dir, "telegram_session.dat")
        session_string = open(session_file).read().strip() if os.path.exists(session_file) else ""

        self.client = TelegramClient(StringSession(session_string), self.api_id, self.api_hash, device_model="SuperAgent")

        # 🔴 FIX 3.2: Reconnect Storm Backoff
        max_retries = 8
        connected = False
        for attempt in range(max_retries):
            try:
                if not self.running: return
                await self.client.connect()
                connected = True
                break
            except Exception as e:
                wait_time = min(300, 2 ** attempt)
                logger.warning(f"Connessione fallita. Riprovo tra {wait_time}s...")
                await asyncio.sleep(wait_time)
                
        if not connected:
            self.running = False
            return

        if not await self.client.is_user_authorized():
            self.running = False
            await self.client.disconnect()
            return
            
        with open(session_file + ".tmp", "w", encoding="utf-8") as f: f.write(self.client.session.save())
        os.replace(session_file + ".tmp", session_file)

        @self.client.on(events.NewMessage(chats=self.selected_chats if self.selected_chats else None))
        async def handler(event):
            if not self.running: return
            self.last_heartbeat = time.monotonic()
            msg = event.raw_text
            
            if self.message_queue:
                # 🔴 FIX 3.1: Throttle anti-flood (Drop oldest)
                if self.message_queue.qsize() > 100:
                    try: self.message_queue.get_nowait()
                    except: pass
                try: self.message_queue.put_nowait(msg)
                except Full: pass
            else:
                self.message_received.emit(msg)

        async def keep_alive():
            consecutive_fails = 0
            while self.running:
                try:
                    self.last_heartbeat = time.monotonic()
                    if not self.client.is_connected(): await self.client.connect()
                    await asyncio.wait_for(self.client.get_me(), timeout=15.0)
                    consecutive_fails = 0
                except asyncio.CancelledError: break
                except Exception:
                    consecutive_fails += 1
                    if consecutive_fails >= 3:
                        self.running = False
                        if self.client: await self.client.disconnect()
                        break
                await asyncio.sleep(30)

        self.keep_alive_task = self.loop.create_task(keep_alive())
        try: await self.client.run_until_disconnected()
        except asyncio.CancelledError: pass
        finally: self.running = False

    def stop(self):
        self.running = False
        if self.loop and self.loop.is_running():
            async def shutdown():
                if self.keep_alive_task: self.keep_alive_task.cancel()
                if self.client: await self.client.disconnect()
            try: asyncio.run_coroutine_threadsafe(shutdown(), self.loop)
            except: pass
        self.quit(); self.wait(2000)