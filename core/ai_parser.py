import json
import logging
import re
import requests
import os

class AIParser:
    def __init__(self, api_key=None, logger=None):
        self.logger = logger or logging.getLogger("AIParser")
        self.api_key = api_key
        # Endpoint standard per OpenRouter
        self.api_url = "https://openrouter.ai/api/v1/chat/completions"
        self.model = "meta-llama/llama-3-70b-instruct"
        
        # Carica le traduzioni dei mercati (addestrate dalla UI)
        self.market_mappings = self._load_market_mappings()

    def _load_market_mappings(self):
        """Legge le traduzioni dei mercati dal database di addestramento."""
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        mapping_file = os.path.join(base_dir, 'config', 'market_mapping.json')
        
        try:
            if os.path.exists(mapping_file):
                with open(mapping_file, 'r', encoding='utf-8') as f:
                    mappings = json.load(f)
                    self.logger.info(f"🧠 Caricati {len(mappings)} mercati addestrati.")
                    return mappings
        except Exception as e:
            self.logger.warning(f"⚠️ Errore caricamento market_mapping.json: {e}")
        
        return {} # Ritorna dizionario vuoto se il file non esiste ancora

    def parse_signal(self, raw_text):
        """
        Elabora il segnale di Telegram tramite OpenRouter e blinda l'output JSON.
        Restituisce un dizionario pronto per essere passato a Playwright e ai Robot.
        """
        self.logger.info(f"🧠 Richiesta analisi AI in corso per: '{raw_text}'")
        
        ai_response = self._call_openrouter(raw_text)
        if not ai_response:
            return None
            
        return self._extract_and_validate_json(ai_response)

    def _call_openrouter(self, user_text):
        """Chiama l'API di OpenRouter costringendo il modello a restituire un JSON."""
        if not self.api_key:
            self.logger.warning("⚠️ API Key OpenRouter mancante. Avvio simulazione (Mock) per test.")
            return '{"teams": "Juventus", "market": "1", "stake": 0}'
            
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "HTTP-Referer": "https://dom21.local", 
            "X-Title": "Dom21 Bot",
            "Content-Type": "application/json"
        }
        
        # PROMPT INGEGNERIZZATO: Gestione dello Stake Assente
        system_prompt = (
            "Sei un estrattore dati per scommesse sportive. Il tuo unico scopo è estrarre "
            "le squadre, il mercato e la puntata dal testo fornito. "
            "Se la puntata (stake o u) non è specificata nel testo, imposta ASSOLUTAMENTE il valore dello 'stake' a 0. "
            "RISPONDI ESCLUSIVAMENTE CON UN JSON VALIDO. Non aggiungere nessun commento. "
            "Usa esattamente questa struttura: {\"teams\": \"Squadra A - Squadra B\", \"market\": \"Nome Mercato\", \"stake\": 0}"
        )
        
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_text}
            ],
            # Parametri per limitare la "fantasia" dell'AI al minimo
            "temperature": 0.1, 
            "max_tokens": 150
        }
        
        try:
            response = requests.post(self.api_url, headers=headers, json=payload, timeout=15)
            response.raise_for_status()
            return response.json()["choices"][0]["message"]["content"]
        except Exception as e:
            self.logger.error(f"❌ Errore di comunicazione con OpenRouter: {e}")
            return None

    def _extract_and_validate_json(self, ai_response_text):
        """
        Filtro di Sicurezza: Pulisce la risposta e applica il Money Management (Stake 0).
        """
        try:
            # 1. Pulisce la stringa da eventuali formattazioni markdown come ```json ... ```
            clean_text = ai_response_text.strip()
            if clean_text.startswith("```json"):
                clean_text = clean_text.replace("```json", "", 1)
            if clean_text.endswith("```"):
                clean_text = clean_text[:-3]
                
            # 2. Cattura tutto ciò che c'è tra parentesi graffe tramite Regex
            json_match = re.search(r'\{.*\}', clean_text, re.DOTALL)
            if not json_match:
                self.logger.error("❌ Formato JSON non rilevato nel testo dell'AI.")
                return None
                
            json_str = json_match.group(0)
            
            # 3. Parsing del JSON stringa in dizionario Python
            parsed_data = json.loads(json_str)
            
            # 4. Validazione Strutturale Base (Teams e Market sono vitali)
            if "teams" not in parsed_data or "market" not in parsed_data:
                self.logger.error(f"❌ JSON Invalido: Mancano le chiavi obbligatorie 'teams' o 'market'")
                return None
            
            # 5. Gestione Sicura dello Stake (Money Management Fallback)
            if "stake" not in parsed_data or parsed_data["stake"] is None:
                parsed_data["stake"] = 0.0
                self.logger.info("⚠️ Stake non trovato nel JSON. Impostato a 0.0 (Il Robot gestirà l'importo).")
            else:
                try:
                    parsed_data["stake"] = float(parsed_data["stake"])
                except ValueError:
                    self.logger.warning("⚠️ Stake non numerico. Forzato a 0.0.")
                    parsed_data["stake"] = 0.0
            
            # 6. Pulizia testo
            parsed_data["teams"] = str(parsed_data["teams"]).strip()
            original_market = str(parsed_data["market"]).strip()
            
            # 7. Traduzione Mercato (AI Training Mapping)
            # Trasforma il mercato in minuscolo per una ricerca insensibile alle maiuscole/minuscole
            market_key = original_market.lower()
            if market_key in self.market_mappings:
                mapped_market = self.market_mappings[market_key]
                self.logger.info(f"🔄 Mercato tradotto tramite addestramento: '{original_market}' -> '{mapped_market}'")
                parsed_data["market"] = mapped_market
            else:
                parsed_data["market"] = original_market
            
            self.logger.info(f"✅ Dati AI Filtrati e Pronti: {parsed_data}")
            return parsed_data
            
        except json.JSONDecodeError as e:
            self.logger.error(f"❌ L'AI ha restituito un JSON corrotto: {e}\nTesto: {ai_response_text}")
            return None
        except Exception as e:
            self.logger.error(f"❌ Errore Critico nel filtro AI Parser: {e}")
            return None
