import json
import os
import requests
import logging
import time

DEFAULT_API_URL = "https://openrouter.ai/api/v1/chat/completions"

class AISignalParser:
    def __init__(self, api_key=None):
        self.logger = logging.getLogger("SuperAgent")
        self.api_key = api_key
        self.model = "google/gemini-2.0-flash-001"
        self.api_url = os.environ.get("OPENROUTER_API_URL", DEFAULT_API_URL)

    def parse(self, telegram_text):
        if not telegram_text or len(telegram_text) < 5:
            return {}

        if not self.api_key:
            self.logger.warning("⚠️ AI PARSER: API key missing (Vault).")
            return {}

        system_instructions = """
        You are an algorithmic betting parser.
        RULES:
        1. Extract teams (e.g. "Team A - Team B").
        2. Extract score (e.g. "6 - 0").
        3. Calculate Market: Sum of scores + 0.5 (e.g. 6+0=6 -> "Over 6.5").
        OUTPUT JSON: {"teams": "...", "market": "Over X.5", "score_detected": "X-Y"}
        """
        for attempt in range(3):
            try:
                response = requests.post(
                    url=self.api_url,
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                        "HTTP-Referer": "http://localhost:8000",
                        "X-Title": "SuperAgentBot"
                    },
                    json={
                        "model": self.model,
                        "messages": [
                            {"role": "system", "content": system_instructions},
                            {"role": "user", "content": telegram_text}
                        ],
                        "temperature": 0.1
                    },
                    timeout=(5, 10)
                )

                if response.status_code == 200:
                    raw = response.json()['choices'][0]['message']['content']
                    
                    # 🛡️ 10/10 GOD MODE PARSING: True Bracket Counter O(n)
                    clean = None
                    in_string = False
                    escape_char = False
                    bracket_count = 0
                    start_idx = -1

                    for i, char in enumerate(raw):
                        if char == '"' and not escape_char:
                            in_string = not in_string
                        
                        if not in_string:
                            if char == '{':
                                if bracket_count == 0:
                                    start_idx = i
                                bracket_count += 1
                            elif char == '}':
                                if bracket_count > 0:
                                    bracket_count -= 1
                                    if bracket_count == 0 and start_idx != -1:
                                        clean = raw[start_idx:i+1]
                                        break  # Primo JSON root isolato con successo
                                        
                        escape_char = (char == '\\' and not escape_char)
                    
                    if not clean:
                        self.logger.error("❌ AI error: Nessun oggetto JSON valido estratto (Bracket Counter fallito).")
                        continue
                        
                    try:
                        data = json.loads(clean)
                        self.logger.info(f"✅ AI OUTPUT: {data}")
                        return data
                    except json.JSONDecodeError as e:
                        self.logger.error(f"❌ AI JSON Parse error: {e} su stringa: {clean}")
                        continue

                elif response.status_code == 429:
                    self.logger.warning(f"⚠️ Rate limit. Retry {attempt + 1}/3...")
                    time.sleep(2 ** (attempt + 1))
                    continue
                else:
                    self.logger.error(f"❌ AI error: {response.status_code}")
                    break

            except requests.exceptions.Timeout:
                self.logger.warning(f"⏱️ AI timeout (attempt {attempt + 1}/3)")
                time.sleep(1)
            except Exception as e:
                self.logger.error(f"❌ AI exception (attempt {attempt + 1}/3): {e}")
                time.sleep(1)

        return {}