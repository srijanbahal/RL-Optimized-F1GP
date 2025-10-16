import random
from src.env.car import Car
from src.env.track import Track

class RaceEnvironment:
    def __init__(self, num_agents: int = 3):
        self.track = Track()
        self.agents = [Car(i) for i in range(num_agents)]
        self.time_step = 0

    def reset(self):
        self.agents = [Car(i) for i in range(len(self.agents))]
        self.time_step = 0
        return [agent.get_state() for agent in self.agents]

    def step(self, actions):
        self.time_step += 1
        for i, agent in enumerate(self.agents):
            if not agent.done:
                agent.update(actions[i])

        done_flags = [a.done or self.track.is_finished(a.position) for a in self.agents]
        return [agent.get_state() for agent in self.agents], done_flags
