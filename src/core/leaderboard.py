from typing import List
from src.env.car import Car

class Leaderboard:
    def __init__(self):
        pass

    def update(self, agents: List[Car]):
        sorted_agents = sorted(agents, key=lambda x: x.position, reverse=True)
        print("\n🏁 --- Leaderboard --- 🏁")
        for rank, agent in enumerate(sorted_agents, start=1):
            print(
                f"{rank}. Car-{agent.id} | "
                f"Pos: {agent.position:6.2f} | "
                f"Speed: {agent.speed:4.2f} | "
                f"Fuel: {agent.fuel:4.2f} | "
                f"Tire: {agent.tire_wear:4.2f}"
            )
        print("-" * 40)
