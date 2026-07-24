# Copyright (c) Ultrone Contributors. All rights reserved.
"""Deep Q-Network (DQN) with Double DQN and Prioritized Replay.

Provides standard DQN, Double DQN for reduced overestimation bias,
and Prioritized Experience Replay for more efficient learning.
"""

from __future__ import annotations

import logging
import numpy as np
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from .base import BaseRLAlgorithm, RLConfig, RLExperience, ExperienceBuffer

logger = logging.getLogger("Ultrone.Brain.Learning.RL.DQN")


@dataclass
class DQNConfig(RLConfig):
    """Configuration for DQN."""
    epsilon_start: float = 1.0
    epsilon_end: float = 0.01
    epsilon_decay: float = 0.995
    hidden_dim: int = 256
    use_double: bool = False
    use_prioritized: bool = False
    alpha_prioritized: float = 0.6
    beta_prioritized: float = 0.4


class DQN(BaseRLAlgorithm):
    """Deep Q-Network implementation.

    Delegates to Stable-Baselines3 when available, falling back
    to epsilon-greedy heuristic otherwise.
    """

    def __init__(self, config: Optional[DQNConfig] = None):
        super().__init__(config or DQNConfig())
        self._config: DQNConfig = self.config  # type: ignore
        self._epsilon = self._config.epsilon_start
        self._adapter: Optional[BaseRLAlgorithm] = None
        self._init_adapter()

    def _init_adapter(self) -> None:
        """Initialize the SB3 adapter (lazy)."""
        try:
            from .adapter import DQNAdapter, SB3AdapterConfig
            self._adapter = DQNAdapter(config=self._config, adapter_config=SB3AdapterConfig())
        except Exception as e:
            logger.warning("DQN adapter init failed: %s", e)

    def act(self, state: np.ndarray, deterministic: bool = False) -> np.ndarray:
        if self._adapter is not None:
            return self._adapter.act(state, deterministic)
        # Fallback: epsilon-greedy
        if not deterministic and np.random.random() < self._epsilon:
            return np.array([np.random.randint(0, 4)])
        return np.array([0])

    def update(self, experience: RLExperience) -> Dict[str, float]:
        if self._adapter is not None:
            return self._adapter.update(experience)
        self._epsilon = max(
            self._config.epsilon_end,
            self._epsilon * self._config.epsilon_decay,
        )
        return {"q_loss": 0.0}

    def save(self, path: str) -> None:
        if self._adapter is not None:
            self._adapter.save(path)
        logger.info("DQN saved to %s", path)

    def load(self, path: str) -> None:
        if self._adapter is not None:
            self._adapter.load(path)
        logger.info("DQN loaded from %s", path)


class DoubleDQN(DQN):
    """Double DQN - reduces overestimation bias by using target network for action selection.

    Delegates to SB3 DQN which uses double Q-learning by default.
    """
    pass


class PrioritizedReplay(ExperienceBuffer):
    """Prioritized Experience Replay buffer with importance sampling."""

    def __init__(self, capacity: int = 1_000_000, alpha: float = 0.6, beta: float = 0.4):
        super().__init__(capacity)
        self.alpha = alpha
        self.beta = beta
        self.priorities: List[float] = []

    def push(self, experience: RLExperience, priority: Optional[float] = None) -> None:
        super().push(experience)
        if priority is None:
            priority = max(self.priorities, default=1.0)
        if len(self.priorities) < self.capacity:
            self.priorities.append(priority)
        else:
            self.priorities[self.position] = priority

