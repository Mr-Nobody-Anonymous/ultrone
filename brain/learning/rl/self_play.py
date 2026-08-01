# Copyright (c) Ultrone Contributors. All rights reserved.
"""Self-play learning wrapper for adversarial training.

Self-play enables agents to improve by playing against copies of
themselves or past checkpoints, creating an automatic curriculum.
"""

from __future__ import annotations

import logging
import copy
import numpy as np
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Union

from .base import BaseRLAlgorithm, RLConfig, RLExperience

logger = logging.getLogger("Ultrone.Brain.Learning.RL.SelfPlay")


@dataclass
class SelfPlayConfig(RLConfig):
    """Configuration for self-play."""
    opponent_pool_size: int = 5
    update_opponent_every: int = 10
    swap_probability: float = 0.5
    use_historical: bool = True


class SelfPlay(BaseRLAlgorithm):
    """Self-play wrapper that maintains an opponent pool.

    The main agent plays against past versions of itself, creating
    an automatic curriculum of increasing difficulty.
    """

    def __init__(self, inner_agent: Optional[BaseRLAlgorithm] = None, config: Optional[SelfPlayConfig] = None):
        """Initialize self-play.
        
        Args:
            inner_agent: The main learning agent to wrap.
            config: Self-play configuration.
        """
        super().__init__(config or SelfPlayConfig())
        self._config: SelfPlayConfig = self.config  # type: ignore
        self._main_agent: Optional[BaseRLAlgorithm] = inner_agent
        self._opponent_pool: List[BaseRLAlgorithm] = []
        self._episodes_since_update = 0

    def set_main_agent(self, agent: BaseRLAlgorithm) -> None:
        """Set the main learning agent."""
        self._main_agent = agent

    def get_opponent(self) -> Optional[BaseRLAlgorithm]:
        """Sample an opponent from the pool."""
        if not self._opponent_pool:
            return self._main_agent
        if np.random.random() < self._config.swap_probability:
            return np.random.choice(self._opponent_pool)
        return self._main_agent

    def update_opponent_pool(self) -> None:
        """Add current agent to opponent pool."""
        if self._main_agent is None:
            return
        self._episodes_since_update += 1
        if self._episodes_since_update >= self._config.update_opponent_every:
            self._opponent_pool.append(copy.deepcopy(self._main_agent))
            if len(self._opponent_pool) > self._config.opponent_pool_size:
                self._opponent_pool.pop(0)
            self._episodes_since_update = 0
            logger.info("Self-play: opponent pool size = %d", len(self._opponent_pool))

    def act(self, state: np.ndarray, deterministic: bool = False) -> np.ndarray:
        if self._main_agent:
            return self._main_agent.act(state, deterministic)
        return np.array([0.0])

    def update(self, experience: RLExperience) -> Dict[str, float]:
        if self._main_agent:
            return self._main_agent.update(experience)
        return {}

    def save(self, path: str) -> None:
        logger.info("SelfPlay save to %s (stub)", path)

    def load(self, path: str) -> None:
        logger.info("SelfPlay load from %s (stub)", path)

    def get_stats(self) -> Dict[str, Any]:
        stats = super().get_stats()
        stats["inner_algorithm"] = type(self._main_agent).__name__ if self._main_agent else "None"
        return stats
