# Copyright (c) Ultrone Contributors. All rights reserved.
"""Base interface for all Reinforcement Learning algorithms.

Every RL algorithm in this module implements ``BaseRLAlgorithm`` so they
can be swapped at runtime in the training pipeline.
"""

from __future__ import annotations

import logging
import numpy as np
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple, TypeVar

logger = logging.getLogger("Ultrone.Brain.Learning.RL.Base")

# Type aliases
Observation = TypeVar("Observation")
Action = TypeVar("Action")


@dataclass
class RLConfig:
    """Base configuration for RL algorithms."""
    learning_rate: float = 3e-4
    gamma: float = 0.99
    tau: float = 0.005
    batch_size: int = 256
    buffer_size: int = 1_000_000
    warmup_steps: int = 1000
    update_every: int = 1
    device: str = "cpu"
    seed: int = 42


@dataclass
class RLExperience:
    """A single transition experience."""
    state: np.ndarray
    action: np.ndarray
    reward: float
    next_state: np.ndarray
    done: bool
    info: Dict[str, Any] = field(default_factory=dict)


class ExperienceBuffer:
    """Circular replay buffer for experience replay."""

    def __init__(self, capacity: int = 1_000_000):
        self.capacity = capacity
        self.buffer: List[RLExperience] = []
        self.position = 0

    def push(self, experience: RLExperience) -> None:
        if len(self.buffer) < self.capacity:
            self.buffer.append(experience)
        else:
            self.buffer[self.position] = experience
        self.position = (self.position + 1) % self.capacity

    def sample(self, batch_size: int) -> List[RLExperience]:
        indices = np.random.randint(0, len(self.buffer), size=batch_size)
        return [self.buffer[i] for i in indices]

    def __len__(self) -> int:
        return len(self.buffer)


@dataclass
class RLMetrics:
    """Training metrics collected during RL training."""
    episode_rewards: List[float] = field(default_factory=list)
    episode_lengths: List[int] = field(default_factory=list)
    losses: Dict[str, List[float]] = field(default_factory=dict)
    avg_reward: float = 0.0
    avg_length: float = 0.0
    total_steps: int = 0
    total_episodes: int = 0

    def update(self, reward: float, length: int, losses: Optional[Dict[str, float]] = None) -> None:
        self.episode_rewards.append(reward)
        self.episode_lengths.append(length)
        self.total_episodes += 1
        window = min(100, len(self.episode_rewards))
        self.avg_reward = sum(self.episode_rewards[-window:]) / window
        self.avg_length = sum(self.episode_lengths[-window:]) / window
        if losses:
            for k, v in losses.items():
                self.losses.setdefault(k, []).append(v)


class BaseRLAlgorithm(ABC):
    """Abstract interface every RL algorithm must implement.

    Follows a Gymnasium-style environment interface for interchangeability.
    """

    def __init__(self, config: RLConfig):
        self.config = config
        self.metrics = RLMetrics()
        self._total_steps = 0
        self._episode_steps = 0
        self._episode_reward = 0.0
        self._is_training = True

    @abstractmethod
    def act(self, state: np.ndarray, deterministic: bool = False) -> np.ndarray:
        """Select an action given the current state."""
        ...

    @abstractmethod
    def update(self, experience: RLExperience) -> Dict[str, float]:
        """Update the algorithm using a single experience.

        Returns a dict of loss values for logging.
        """
        ...

    @abstractmethod
    def save(self, path: str) -> None:
        """Save model parameters to disk."""
        ...

    @abstractmethod
    def load(self, path: str) -> None:
        """Load model parameters from disk."""
        ...

    def train(self) -> None:
        """Set the algorithm to training mode."""
        self._is_training = True

    def eval(self) -> None:
        """Set the algorithm to evaluation mode."""
        self._is_training = False

    def reset_episode(self) -> None:
        """Reset episode tracking variables."""
        self._episode_steps = 0
        self._episode_reward = 0.0

    def get_stats(self) -> Dict[str, Any]:
        """Return diagnostic statistics."""
        return {
            "type": type(self).__name__,
            "total_steps": self._total_steps,
            "total_episodes": self.metrics.total_episodes,
            "avg_reward": self.metrics.avg_reward,
            "avg_length": self.metrics.avg_length,
            "learning_rate": self.config.learning_rate,
            "gamma": self.config.gamma,
        }


class RLTrainer:
    """High-level trainer that orchestrates RL training loops.

    Works with any ``BaseRLAlgorithm`` implementation.
    """

    def __init__(
        self,
        algorithm: BaseRLAlgorithm,
        env: Any,
        config: Optional[RLConfig] = None,
    ):
        self.algorithm = algorithm
        self.env = env
        self.config = config or RLConfig()
        self.buffer = ExperienceBuffer(self.config.buffer_size)

    def train_episode(self, max_steps: int = 1000) -> Dict[str, Any]:
        """Train for a single episode."""
        state, _ = self.env.reset()
        self.algorithm.reset_episode()
        episode_losses: Dict[str, List[float]] = {}

        for step in range(max_steps):
            action = self.algorithm.act(state)
            next_state, reward, done, truncated, info = self.env.step(action)
            exp = RLExperience(
                state=state,
                action=action,
                reward=reward,
                next_state=next_state,
                done=done or truncated,
                info=info,
            )
            self.buffer.push(exp)
            self.algorithm._total_steps += 1
            self.algorithm._episode_steps += 1
            self.algorithm._episode_reward += reward

            if len(self.buffer) > self.config.warmup_steps:
                batch = self.buffer.sample(self.config.batch_size)
                for exp_b in batch:
                    losses = self.algorithm.update(exp_b)
                    for k, v in losses.items():
                        episode_losses.setdefault(k, []).append(v)

            state = next_state
            if done or truncated:
                break

        avg_losses = {k: float(np.mean(v)) for k, v in episode_losses.items()}
        self.algorithm.metrics.update(
            reward=self.algorithm._episode_reward,
            length=self.algorithm._episode_steps,
            losses=avg_losses,
        )
        return {
            "reward": self.algorithm._episode_reward,
            "length": self.algorithm._episode_steps,
            "losses": avg_losses,
        }

    def train(self, num_episodes: int = 1000, max_steps: int = 1000) -> RLMetrics:
        """Run full training loop."""
        for ep in range(num_episodes):
            self.train_episode(max_steps)
            if (ep + 1) % 100 == 0:
                logger.info(
                    "Episode %d/%d: avg_reward=%.2f, avg_length=%.1f",
                    ep + 1, num_episodes,
                    self.algorithm.metrics.avg_reward,
                    self.algorithm.metrics.avg_length,
                )
        return self.algorithm.metrics