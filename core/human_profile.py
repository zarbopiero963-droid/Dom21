import math
import random

class HumanProfile:
    def __init__(self, profile_type="average"):
        self.profile_type = profile_type
        self.mood_drift = 1.0

    def update_mood(self):
        self.mood_drift = random.uniform(0.9, 1.2)

    def get_hesitation(self, base_ms=500):
        try:
            val = random.lognormvariate(math.log(base_ms), 0.3) * self.mood_drift
            return max(100, min(val, base_ms * 3)) / 1000.0
        except: return base_ms / 1000.0

    def get_key_press_duration(self):
        return random.randint(40, 120) / 1000.0 * self.mood_drift

    def get_mouse_speed(self):
        return int(random.uniform(15, 35) * self.mood_drift)