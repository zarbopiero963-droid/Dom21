import time
import random
import math
import logging

class HumanMouse:
    def __init__(self, page, profile, logger=None):
        self.page = page
        self.profile = profile
        self.logger = logger or logging.getLogger("HumanMouse")
        self.current_x = random.gauss(1920 / 2, 300)
        self.current_y = random.gauss(1080 / 2, 200)

    def _bezier(self, p0, p1, p2, p3, t):
        x = (1-t)**3 * p0[0] + 3*(1-t)**2 * t * p1[0] + 3*(1-t) * t**2 * p2[0] + t**3 * p3[0]
        y = (1-t)**3 * p0[1] + 3*(1-t)**2 * t * p1[1] + 3*(1-t) * t**2 * p2[1] + t**3 * p3[1]
        return x, y

    def _dynamic_easing(self, t):
        """L'umano non frena sempre uguale. Sceglie tra frenata morbida, brusca o lineare."""
        easing_type = random.choice(["cubic", "quadratic", "sine"])
        if easing_type == "cubic": return 1 - pow(1 - t, 3)
        elif easing_type == "quadratic": return 1 - pow(1 - t, 2)
        else: return math.sin(t * math.pi / 2)

    def idle_move(self):
        """Movimenti parassiti o di lettura (Idle Behavior)"""
        if random.random() < 0.3: # 30% di probabilità di fare movimenti a vuoto
            drift_x = self.current_x + random.gauss(0, 100)
            drift_y = self.current_y + random.gauss(0, 100)
            self.move_to(drift_x, drift_y, is_idle=True)
            time.sleep(random.uniform(0.5, 2.0))

    def move_to(self, target_x, target_y, is_idle=False):
        dist = math.hypot(target_x - self.current_x, target_y - self.current_y)
        
        # Velocità influenzata dal Profilo e dal Mood Drift
        base_steps = int(max(10, min(dist / 10, 60)) * self.profile.speed_multiplier * self.profile.get_mood_drift())
        steps = int(random.gauss(base_steps, 4))
        if steps < 8: steps = 8

        # Scelta del pattern di approccio (ML Defeat)
        approach_roll = random.random()
        if approach_roll < self.profile.overshoot_prob:
            # OVERSHOOT (Supera il bersaglio e torna indietro)
            end_x = target_x + random.gauss(0, 20)
            end_y = target_y + random.gauss(0, 20)
            needs_correction = True
        elif approach_roll < self.profile.overshoot_prob + 0.15:
            # UNDERSHOOT (Si ferma prima, esita, fa uno scatto finale)
            end_x = target_x - (target_x - self.current_x) * 0.1
            end_y = target_y - (target_y - self.current_y) * 0.1
            needs_correction = True
        else:
            # DIRETTO (Curva naturale, arriva a destinazione)
            end_x, end_y = target_x, target_y
            needs_correction = False

        ctrl_x1 = self.current_x + (end_x - self.current_x) * random.gauss(0.5, 0.2)
        ctrl_y1 = self.current_y + (end_y - self.current_y) * random.gauss(0.5, 0.2)
        ctrl_x2 = end_x + random.gauss(0, 30)
        ctrl_y2 = end_y + random.gauss(0, 30)

        for i in range(1, steps + 1):
            t = i / steps
            eased_t = self._dynamic_easing(t)
            
            x, y = self._bezier((self.current_x, self.current_y), (ctrl_x1, ctrl_y1), (ctrl_x2, ctrl_y2), (end_x, end_y), eased_t)
            
            # Jitter scollegato dalla distanza (Puro tremore nervoso basato sull'identità)
            x += random.gauss(0, self.profile.base_jitter)
            y += random.gauss(0, self.profile.base_jitter)
            
            self.page.mouse.move(max(0, min(x, 1920)), max(0, min(y, 1080)))
            time.sleep(random.lognormvariate(-4.5, 0.3) * self.profile.speed_multiplier) 

        self.current_x, self.current_y = end_x, end_y

        # CORRECTION LOOP: Se abbiamo fatto over/undershoot, aggiustiamo la mira
        if needs_correction and not is_idle:
            time.sleep(random.uniform(0.05, 0.15)) # Esitazione prima di accorgersi dell'errore
            self.move_to(target_x, target_y) # Movimento ricorsivo per centrare il bersaglio

    def click(self, locator):
        try:
            element = locator.first
            element.wait_for(state="visible", timeout=8000)
            box = element.bounding_box()
            if not box: return
            
            target_x = random.gauss(box['x'] + box['width'] / 2, box['width'] / 6)
            target_y = random.gauss(box['y'] + box['height'] / 2, box['height'] / 6)
            
            # 1. Movimenti parassiti pre-click
            self.idle_move()
            
            # 2. Movimento reale
            self.move_to(target_x, target_y)
            
            # 3. Latenza Cognitiva basata sul profilo (esitazione)
            import math
            time.sleep(self.profile.get_hesitation())
            
            self.page.mouse.down()
            dwell = random.gauss(0.08, 0.02) * self.profile.speed_multiplier
            time.sleep(max(0.02, dwell))
            self.page.mouse.up()
            
        except Exception as e:
            self.logger.warning(f"Errore click: {e}")
            locator.click()
