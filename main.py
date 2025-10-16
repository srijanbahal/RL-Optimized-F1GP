from src.env.race_env import RaceEnvironment
from src.core.leaderboard import Leaderboard
import random, time, os

def clear(): os.system("cls" if os.name=="nt" else "clear")

def run():
    env = RaceEnvironment(n=4, laps=3)
    board = Leaderboard()
    while not env.finished():
        clear()
        acts = [random.uniform(-1,1) for _ in env.cars]
        env.step(acts)
        board.update(env)
        time.sleep(0.25)
    print("\n🏆 Race complete!")

if __name__ == "__main__":
    run()
