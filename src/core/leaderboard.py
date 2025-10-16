class Leaderboard:
    def update(self, env):
        sorted_cars = sorted(zip(env.cars, env.laps),
                             key=lambda x:(x[1], x[0].pos),
                             reverse=True)
        print("\n🏁 --- Leaderboard --- 🏁")
        for rank,(car,lap) in enumerate(sorted_cars,start=1):
            print(f"{rank}. Car-{car.id} | Lap {lap}/{env.total_laps} "
                  f"| Pos {car.pos:6.0f}m | Speed {car.speed:5.1f} "
                  f"| Fuel {car.fuel:5.1f} | Wear {car.tyre_wear:4.2f} | Dmg {car.damage:4.2f}")
        print("-"*70)
