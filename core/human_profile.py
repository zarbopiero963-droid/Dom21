import random
import time

class SyntheticProfile:
    """
    🧬 SUPERAGENT OS - PROFILAZIONE SINTETICA
    Genera un'identità umana persistente per l'intera sessione.
    Definisce i tratti motori e cognitivi per sconfiggere i modelli ML.
    """
    def __init__(self):
        profiles = ["tech_savvy", "average_distracted", "elderly_slow", "nervous_impulsive"]
        self.type = random.choice(profiles)
        self.session_start = time.time()
        
        # DNA Motorio e Cognitivo basato sul tipo di profilo
        if self.type == "tech_savvy":
            self.speed_multiplier = random.uniform(0.7, 0.9)  # Più veloce (meno tempo)
            self.error_rate = random.uniform(0.01, 0.02)
            self.overshoot_prob = 0.15 # Va dritto al bersaglio
            self.hesitation_base = random.uniform(0.05, 0.15)
        elif self.type == "average_distracted":
            self.speed_multiplier = random.uniform(1.0, 1.3)
            self.error_rate = random.uniform(0.04, 0.07)
            self.overshoot_prob = 0.40 # Spesso va oltre e corregge
            self.hesitation_base = random.uniform(0.3, 0.8) # Si distrae
        elif self.type == "elderly_slow":
            self.speed_multiplier = random.uniform(1.5, 2.2)
            self.error_rate = random.uniform(0.03, 0.05)
            self.overshoot_prob = 0.20
            self.hesitation_base = random.uniform(0.6, 1.2) # Molto lento a decidere
        else: # nervous_impulsive
            self.speed_multiplier = random.uniform(0.8, 1.1)
            self.error_rate = random.uniform(0.06, 0.10) # Molti errori per la fretta
            self.overshoot_prob = 0.60 # Sbaglia mira spessissimo
            self.hesitation_base = random.uniform(0.1, 0.2)
            
        self.base_jitter = random.uniform(1.0, 3.5)

    def get_mood_drift(self):
        """Simula la stanchezza e la perdita di focus nel tempo (Session Drift)"""
        elapsed_minutes = (time.time() - self.session_start) / 60.0
        # Dopo 5 minuti inizia ad accumulare stanchezza (max 30% di lentezza in più)
        tiredness_factor = min(0.3, elapsed_minutes * 0.02)
        return 1.0 + tiredness_factor

    def get_current_error_rate(self):
        """L'errore aumenta se l'utente si stanca"""
        return self.error_rate * self.get_mood_drift()

    def get_hesitation(self):
        """Calcola la latenza cognitiva attuale basata sull'identità"""
        base = self.hesitation_base * self.get_mood_drift()
        # LogNormale dinamica
        return random.lognormvariate(math.log(base), 0.3)