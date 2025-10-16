import random

class Car:
    def __init__(self, car_id: int):
        self.id = car_id
        self.position = 0.0
        self.speed = 0.0
        self.fuel = 1.0
        self.tire_wear = 0.0
        self.done = False

    def update(self, action: int):
        """
        action = 0 -> brake
        action = 1 -> maintain
        action = 2 -> accelerate
        """
        accel = {0: -0.05, 1: 0.0, 2: 0.05}[action]
        self.speed = max(0.0, min(1.0, self.speed + accel))
        self.position += self.speed * 10.0  # scaled for visibility
        self.fuel -= 0.002 + self.speed * 0.001  # faster drains more fuel
        self.tire_wear += self.speed * 0.002

        # Random failure chance (adds realism)
        if random.random() < 0.001:
            self.speed *= 0.5

        if self.fuel <= 0:
            self.done = True

    def get_state(self):
        return {
            "id": self.id,
            "position": self.position,
            "speed": self.speed,
            "fuel": self.fuel,
            "tire_wear": self.tire_wear,
            "done": self.done,
        }
