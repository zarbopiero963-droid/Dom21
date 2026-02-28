import time
import random
from core.geometry import generate_bezier_curve, clamp_point

class HumanMouse:
    def __init__(self, page, profile):
        self.page = page
        self.profile = profile
        self.current_x = self.current_y = None

    def move_to(self, target_x, target_y, depth=0):
        viewport = self.page.viewport_size
        if not viewport: viewport = {"width": 1920, "height": 1080}

        if self.current_x is None or self.current_y is None:
            self.current_x = random.randint(100, viewport["width"] - 100)
            self.current_y = random.randint(100, viewport["height"] - 100)

        target_x, target_y = clamp_point(target_x, target_y, viewport)
        cp1_x = self.current_x + (target_x - self.current_x) * random.uniform(0.1, 0.4)
        cp1_y = self.current_y + (target_y - self.current_y) * random.uniform(-0.5, 0.5)
        
        curve = generate_bezier_curve((self.current_x, self.current_y), (cp1_x, cp1_y), (target_x, target_y), self.profile.get_mouse_speed())

        for x, y in curve:
            cx, cy = clamp_point(x, y, viewport)
            try:
                self.page.mouse.move(cx, cy)
                self.current_x, self.current_y = cx, cy
                time.sleep(random.uniform(0.002, 0.008))
            except: break

        if random.random() < 0.2 and depth < 2:
            self.move_to(target_x + random.randint(-15, 15), target_y + random.randint(-15, 15), depth=depth+1)
            time.sleep(self.profile.get_hesitation(100))
            self.move_to(target_x, target_y, depth=depth+1)
        elif depth >= 2:
            try:
                self.page.mouse.move(target_x, target_y)
                self.current_x, self.current_y = target_x, target_y
            except: pass

    def click(self, target_x, target_y):
        self.move_to(target_x, target_y)
        time.sleep(self.profile.get_hesitation(150))
        try:
            self.page.mouse.down()
            time.sleep(self.profile.get_key_press_duration())
            self.page.mouse.up()
        except: pass