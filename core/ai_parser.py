import json
import logging
import re
import requests

class AIParser:
    def __init__(self, api_key=None, logger=None):
        self.logger = logger or logging.getLogger("AIParser")
        self.api_key = api_key
        # Endpoint standard per OpenRouter (usato in ui/roserpina_tab.py)
        self.api_url = "https://openrouter.ai/api/v1/chat/completions"
        self.model = "meta-llama/llama-3-70b-instruct"

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
            return '{"teams": "Juventus", "market": "1", "stake": 10}'
            
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "HTTP-Referer": "https://dom21.local", 
            "X-Title": "Dom21 Bot",
            "Content-Type": "application/json"
        }
        
        # PROMPT INGEGNERIZZATO: Impediamo all'AI di essere discorsiva
        system_prompt = (
            "Sei un estrattore dati per scommesse sportive. Il tuo unico scopo è estrarre "
            "le squadre, il mercato e la puntata dal testo fornito. "
            "RISPONDI ESCLUSIVAMENTE CON UN JSON VALIDO. Non aggiungere nessun commento. "
            "Usa esattamente questa struttura: {\"teams\": \"Squadra A - Squadra B\", \"market\": \"1\", \"stake\": 10}"
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
        Filtro di Sicurezza: Pulisce la risposta da eventuali markdown o allucinazioni testuali
        ed estrae i dati in modo matematico.
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
            
            # 3. Tenta il parsing del JSON stringa in dizionario Python
            parsed_data = json.loads(json_str)
            
            # 4. Validazione Strutturale (I campi vitali per il DomExecutor Playwright)
            required_keys = ["teams", "market", "stake"]
            for key in required_keys:
                if key not in parsed_data:
                    self.logger.error(f"❌ JSON Invalido: Manca la chiave obbligatoria '{key}'")
                    return None
            
            # 5. Type Casting Sicuro (evita che lo stake arrivi come stringa mandando in crash la schedina)
            parsed_data["stake"] = float(parsed_data["stake"])
            parsed_data["teams"] = str(parsed_data["teams"]).strip()
            parsed_data["market"] = str(parsed_data["market"]).strip()
            
            self.logger.info(f"✅ Dati AI Filtrati e Validati: {parsed_data}")
            return parsed_data
            
        except json.JSONDecodeError as e:
            self.logger.error(f"❌ L'AI ha restituito un JSON corrotto: {e}\nTesto originale: {ai_response_text}")
            return None
        except ValueError as e:
            self.logger.error(f"❌ Errore di tipo (es. Stake non convertibile in numero): {e}")
            return None
        except Exception as e:
            self.logger.error(f"❌ Errore Critico nel filtro AI Parser: {e}")
            return None
