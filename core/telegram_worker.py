import logging
import threading
import time
import os

try:
    import telebot
except ImportError:
    telebot = None

class TelegramWorker:
    def __init__(self, token, allowed_chat_ids=None, logger=None):
        self.logger = logger or logging.getLogger("TelegramWorker")
        self.token = token
        
        # Converte la lista di ID autorizzati in stringhe per sicurezza
        self.allowed_chat_ids = [str(chat_id) for chat_id in (allowed_chat_ids or [])]
        
        self.bot = telebot.TeleBot(self.token) if telebot and self.token else None
        self.is_running = False
        self.message_callback = None
        self._polling_thread = None

    def start(self, on_message_callback):
        """Avvia il listener di Telegram in un thread separato."""
        if not self.bot:
            self.logger.error("❌ Impossibile avviare Telegram: Token mancante o libreria 'pyTelegramBotAPI' non installata.")
            self.logger.info("💡 Installa la libreria eseguendo: pip install pyTelegramBotAPI")
            return False
            
        self.message_callback = on_message_callback
        self.is_running = True
        
        @self.bot.message_handler(func=lambda message: True)
        def handle_message(message):
            chat_id = str(message.chat.id)
            
            # FILTRO DI SICUREZZA: Ignora messaggi da sconosciuti
            if self.allowed_chat_ids and chat_id not in self.allowed_chat_ids:
                self.logger.warning(f"⚠️ Tentativo di accesso non autorizzato dal Chat ID: {chat_id}")
                return
            
            text = message.text
            if not text:
                return
                
            self.logger.info(f"📥 Nuovo segnale ricevuto da Telegram: {text}")
            
            # Feedback immediato all'utente sul telefono
            self.send_message("⏳ Segnale ricevuto. Analisi AI in corso...", chat_id)
            
            # Passa il messaggio al Controller/Motore AI
            if self.message_callback:
                try:
                    self.message_callback(text, chat_id)
                except Exception as e:
                    self.logger.error(f"❌ Errore interno durante l'elaborazione del segnale: {e}")
                    self.send_message(f"❌ Errore di sistema durante l'elaborazione del segnale.", chat_id)

        # Avvia il polling in background per non bloccare il sistema principale
        self._polling_thread = threading.Thread(target=self._poll, daemon=True)
        self._polling_thread.start()
        self.logger.info("📡 Telegram Worker attivo e in ascolto per nuovi segnali...")
        return True

    def _poll(self):
        """Ciclo di ascolto resiliente ai crash di rete."""
        while self.is_running:
            try:
                # none_stop=True ignora gli errori temporanei dell'API
                self.bot.polling(none_stop=True, interval=1, timeout=20)
            except Exception as e:
                self.logger.error(f"⚠️ Errore di connessione a Telegram. Ritento tra 5 secondi... Dettaglio: {e}")
                time.sleep(5)

    def stop(self):
        """Spegne il worker in modo pulito."""
        self.is_running = False
        if self.bot:
            self.bot.stop_polling()
        self.logger.info("🛑 Telegram Worker disconnesso.")

    def send_message(self, text, chat_id=None):
        """Invia un messaggio di testo su Telegram."""
        if not self.bot:
            self.logger.error("❌ Impossibile inviare messaggio: Bot non configurato.")
            return False
        try:
            # Se non viene specificato il chat_id, invia al primo ID autorizzato della lista (l'Admin)
            target_chat = chat_id if chat_id else (self.allowed_chat_ids[0] if self.allowed_chat_ids else None)
            
            if target_chat:
                self.bot.send_message(target_chat, text)
                return True
            else:
                self.logger.error("❌ Nessun Chat ID valido per inviare il messaggio.")
                return False
        except Exception as e:
            self.logger.error(f"❌ Errore invio messaggio Telegram: {e}")
            return False
            
    def send_photo(self, photo_path, caption="", chat_id=None):
        """Invia uno screenshot o una foto della ricevuta della scommessa."""
        if not self.bot:
            return False
        try:
            target_chat = chat_id if chat_id else (self.allowed_chat_ids[0] if self.allowed_chat_ids else None)
            
            if target_chat and os.path.exists(photo_path):
                with open(photo_path, 'rb') as photo:
                    self.bot.send_photo(target_chat, photo, caption=caption)
                return True
            else:
                self.logger.error(f"❌ File immagine non trovato: {photo_path}")
                return False
        except Exception as e:
            self.logger.error(f"❌ Errore invio foto Telegram: {e}")
            return False
