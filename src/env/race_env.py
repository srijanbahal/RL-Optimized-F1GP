import random
from src.env.car import Car
from src.env.track import Track

class RaceEnvironment:
    def __init__(self, n=4, laps=3):
        self.track = Track()
        self.laps = [0]*n
        self.cars = [Car(i) for i in range(n)]
        self.total_laps = laps
        self.weather = "dry"
        self.safety_car = False
        self.yellow_timer = 0

    def step(self, actions):
        # maybe trigger yellow flag
        if random.random() < 0.002:
            self.safety_car = True
            self.yellow_timer = 30
            print("⚠️  Yellow flag! Safety car deployed.")

        if self.yellow_timer > 0:
            self.yellow_timer -= 1
            if self.yellow_timer == 0:
                self.safety_car = False
                print("✅ Green flag!")

        # sort by position for overtaking logic
        order = sorted(self.cars, key=lambda c: c.pos, reverse=True)
        for idx, car in enumerate(order):
            ahead = order[idx-1] if idx > 0 else None
            sec = self.track.section_at(car.pos)
            car.update(actions[car.id], sec, ahead=ahead, safety=self.safety_car)

            # lap counting
            if car.pos >= self.track.length:
                car.pos -= self.track.length
                self.laps[car.id] += 1

    def finished(self):
        return all(l >= self.total_laps or c.done for l,c in zip(self.laps,self.cars))
