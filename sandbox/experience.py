# Copyright (c) Ultrone Contributors. All rights reserved.
"""Learning from experience, entirely inside the sandbox.

A persistent epsilon-greedy learner faces the same bandit environment
across successive episodes (environment re-seeded each episode; the agent's
knowledge persists). Because exploration decays as its value estimates
stabilize, later episodes should harvest higher reward and incur less
regret than early ones -- a learning *curve*, measured honestly:

- ``episode_mean_reward`` -- per-episode average reward;
- ``episode_regret``      -- per-episode gap vs always playing the best arm;
- ``learns_from_experience`` -- last-episode regret < first-episode regret.
"""

from __future__ import annotations

import random
from typing import Dict, List, Sequence


class BanditEnvironment:
    def __init__(self, arm_probs: Sequence[float], seed: int) -> None:
        self.arm_probs = tuple(arm_probs)
        self.rng = random.Random(seed)

    def pull(self, arm: int) -> int:
        return 1 if self.rng.random() < self.arm_probs[arm] else 0


class EpsilonGreedyLearner:
    def __init__(
        self, n_arms: int, rng: random.Random,
        epsilon_start: float = 0.35, epsilon_decay: float = 0.995,
        epsilon_min: float = 0.03,
    ) -> None:
        self.n_arms = n_arms
        self.rng = rng
        self.epsilon = epsilon_start
        self.epsilon_decay = epsilon_decay
        self.epsilon_min = epsilon_min
        self.counts = [0] * n_arms
        self.totals = [0.0] * n_arms
        self.trials = 0

    def select(self) -> int:
        eps = max(self.epsilon_min, self.epsilon)
        self.epsilon *= self.epsilon_decay
        if self.rng.random() < eps:
            return self.rng.randrange(self.n_arms)
        best_mean = max(
            (self.totals[i] / self.counts[i], -i)
            for i in range(self.n_arms) if self.counts[i]
        ) if any(self.counts) else None
        if best_mean is None:
            return self.trials % self.n_arms
        return -best_mean[1]

    def update(self, arm: int, reward: float) -> None:
        self.counts[arm] += 1
        self.totals[arm] += reward
        self.trials += 1

    def greedy_arm(self) -> int:
        means = [
            (self.totals[i] / self.counts[i] if self.counts[i] else 0.0, -i)
            for i in range(self.n_arms)
        ]
        return -max(means)[1]


def run_learning_curve(
    arm_probs: Sequence[float] = (0.2, 0.5, 0.8),
    seed: int = 0,
    episodes: int = 8,
    steps_per_episode: int = 120,
) -> Dict[str, object]:
    rng = random.Random(seed ^ 0x51EED)
    agent = EpsilonGreedyLearner(len(arm_probs), rng)
    best = max(arm_probs)

    mean_rewards: List[float] = []
    regrets: List[float] = []
    for episode in range(episodes):
        env = BanditEnvironment(arm_probs, seed * 1009 + episode)
        total = 0
        for _ in range(steps_per_episode):
            arm = agent.select()
            reward = env.pull(arm)
            agent.update(arm, reward)
            total += reward
        mean_rewards.append(round(total / steps_per_episode, 4))
        regrets.append(round(best - total / steps_per_episode, 4))

    return {
        "arm_probs": list(arm_probs),
        "episodes": episodes,
        "steps_per_episode": steps_per_episode,
        "episode_mean_reward": mean_rewards,
        "episode_regret": regrets,
        "final_greedy_arm": agent.greedy_arm(),
        "finds_best_arm": agent.greedy_arm() == arm_probs.index(best),
        "learns_from_experience": regrets[-1] < regrets[0],
        "improvement": round(mean_rewards[-1] - mean_rewards[0], 4),
    }
