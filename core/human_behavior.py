import time
import random

class HumanBehavior:
    def __init__(self, page, profile):
        self.page = page
        self.profile = profile

    def type_text(self, selector, text):
        try:
            self.page.click(selector)
            time.sleep(self.profile.get_hesitation(200))
            
            burst_size = random.randint(2, 5)
            count = 0
            
            for char in text:
                try:
                    if char.isalnum() and char.islower():
                        self.page.keyboard.down(char)
                        time.sleep(self.profile.get_key_press_duration())
                        self.page.keyboard.up(char)
                    else:
                        self.page.keyboard.insert_text(char)
                except: self.page.keyboard.insert_text(char)
                    
                time.sleep(random.uniform(0.01, 0.08) * self.profile.mood_drift)
                count += 1
                if count >= burst_size:
                    time.sleep(self.profile.get_hesitation(150))
                    burst_size = random.randint(2, 5)
                    count = 0
            self.profile.update_mood()
        except: pass