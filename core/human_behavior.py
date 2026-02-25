import time
import random
import math
import logging
from core.human_profile import SyntheticProfile

class HumanInput:
    def __init__(self, page, logger=None):
        self.page = page
        self.logger = logger or logging.getLogger("HumanInput")
        # Nasce l'identità dell'utente per questa sessione
        self.profile = SyntheticProfile()
        self.logger.info(f"🧬 Generato Profilo Sintetico: {self.profile.type} (Speed: {self.profile.speed_multiplier:.2f})")

    def type_text(self, text):
        keyboard = self.page.keyboard
        current_error_rate = self.profile.get_current_error_rate()
        
        # BURST LOGIC: Quante lettere scrive prima di fare una pausa cognitiva?
        burst_size = random.randint(2, 6)
        typed_in_burst = 0

        for char in text:
            # 1. ERRORE COGNITIVO (Typo dipendente dal profilo)
            if random.random() < current_error_rate:
                wrong_char = random.choice("abcdefghijklmnopqrstuvwxyz123456789")
                keyboard.press(wrong_char)
                
                # Reazione all'errore (lo shock rallenta se si è stanchi)
                reaction = random.lognormvariate(-1.0, 0.4) * self.profile.get_mood_drift()
                time.sleep(reaction)
                
                keyboard.press("Backspace")
                time.sleep(random.uniform(0.1, 0.25) * self.profile.speed_multiplier)

            # 2. BATTITURA
            keyboard.down(char)
            # Dwell time dinamico
            dwell_time = random.gauss(0.065, 0.02) * self.profile.speed_multiplier
            time.sleep(max(0.015, dwell_time))
            keyboard.up(char)
            
            # 3. BURST E FLIGHT TIME
            typed_in_burst += 1
            if typed_in_burst >= burst_size:
                # Pausa cognitiva (Guarda lo schermo per controllare cosa ha scritto)
                time.sleep(random.lognormvariate(-1.2, 0.5) * self.profile.get_mood_drift())
                burst_size = random.randint(2, 6)
                typed_in_burst = 0
            else:
                # Volo standard verso il tasto successivo
                flight_time = random.lognormvariate(-2.2, 0.3) * self.profile.speed_multiplier
                time.sleep(max(0.03, flight_time))

    def scroll_reading(self):
        """Scroll con identità. Un 'nervous' scrolla veloce, un 'elderly' lentissimo."""
        scrolls = random.randint(2, 4)
        for _ in range(scrolls):
            delta_y = int(random.gauss(300, 100))
            self.page.mouse.wheel(0, delta_y)
            
            # Tempo di lettura dipende dal profilo
            reading_time = random.lognormvariate(0.5, 0.6) * self.profile.speed_multiplier
            time.sleep(reading_time)
            
            # Scroll back (correggere la perdita del segno) dipendente dal profilo
            if random.random() < self.profile.overshoot_prob:
                time.sleep(0.2)
                self.page.mouse.wheel(0, int(random.gauss(-100, 30)))
                time.sleep(random.uniform(0.3, 0.8))
