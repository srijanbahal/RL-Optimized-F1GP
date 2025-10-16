import random, math

class Car:
    def __init__(self, car_id, tyre="soft"):
        self.id = car_id
        self.pos = 0.0
        self.speed = 0.0
        self.accel = 0.0
        self.fuel = 100.0
        self.tyre_wear = 0.0
        self.damage = 0.0
        self.done = False
        self.behind_timer = 0.0   # seconds within DRS range

    def update(self, action, section, ahead=None, safety=False):
        throttle = max(-1, min(1, action))
        grip = max(0.4, 1 - self.tyre_wear - self.damage)

        # base accel, mass, drag
        drag = 0.00045 * self.speed**2
        accel = 30 * throttle * grip - drag

        # slow for corners
        if section.kind == "corner":
            safe_speed = max(30, section.radius * 0.6)
            if self.speed > safe_speed:
                accel -= (self.speed - safe_speed) * 0.3
                self.damage += 0.0005 * (self.speed - safe_speed)

        # slipstream / DRS
        if ahead and ahead.pos - self.pos < 100 and ahead.pos > self.pos:
            self.behind_timer += 0.1
            if section.drs and self.behind_timer > 1.0:
                accel += 10  # boost
        else:
            self.behind_timer = 0.0

        # safety car mode
        if safety:
            accel = min(accel, 0)
            self.speed = min(self.speed, 40)

        # update dynamics
        self.speed = max(0, self.speed + accel * 0.1)
        self.pos += self.speed * 0.1
        self.fuel -= 0.02 * abs(throttle)
        self.tyre_wear += 0.0005 * abs(throttle)
        if self.fuel <= 0 or self.damage >= 1:
            self.done = True
