import random
from sim.fault_injection import FaultSpec, FaultType, FaultyEnv


class F:
    def reset(self, *a, **k):
        return {"red_force": {"health": 100}}

    def step(self, a):
        return self.reset(), 0, False, {}


env = FaultyEnv(F(), (FaultSpec(FaultType.STALE_OBSERVATION, probability=1.0),),
                random.Random(5))
o1 = env.reset()
o2 = env.step(None)[0]
print("stats:", env.stats)
print("specs:", env.specs)
