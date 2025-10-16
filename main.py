from src.env.race_env import RaceEnvironment
from src.core.leaderboard import Leaderboard
import random, time, os

def clear_console():
    os.system("cls" if os.name == "nt" else "clear")

def simulate_race(steps=100, num_agents=3):
    env = RaceEnvironment(num_agents=num_agents)
    leaderboard = Leaderboard()

    for step in range(steps):
        clear_console()
        print(f"Step: {step + 1}")
        actions = [random.choice([0, 1, 2]) for _ in env.agents]
        states, done_flags = env.step(actions)

        leaderboard.update(env.agents)
        if all(done_flags):
            print("\n🏆 Race finished! 🏆")
            break

        time.sleep(0.3)

if __name__ == "__main__":
    simulate_race(steps=80, num_agents=5)
