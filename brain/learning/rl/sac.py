# Copyright (c) Ultrone Contributors. All rights reserved.
"""Soft Actor-Critic (SAC) algorithm.

SAC is an off-policy maximum-entropy RL algorithm that optimizes a
stochastic policy with entropy regularization for improved exploration.
"""

from __future__ import annotations

import logging
import numpy as np
from dataclasses import dataclass
from typing import Any, Dict, Optional

from .base import BaseRLAlgorithm, RLConfig, RLExperience

logger = logging.getLogger("Ultrone.Brain.Learning.RL.SAC")


@dataclass
class SACConfig(RLConfig):
    """Configuration for SAC algorithm."""
    alpha: float = 0.2
    automatic_entropy_tuning: bool = True
    target_entropy: Optional[float] = None
    hidden_dim: int = 256
    num_layers: int = 2


class SAC(BaseRLAlgorithm):
    """Soft Actor-Critic implementation.

    Combines off-policy Q-learning with maximum entropy RL for
    sample-efficient, stable training.

    Delegates to Stable-Baselines3 when available, falling back
    to heuristic policy otherwise.
    """

    def __init__(self, config: Optional[SACConfig] = None):
        super().__init__(config or SACConfig())
        self._config: SACConfig = self.config  # type: ignore
        self._adapter: Optional[BaseRLAlgorithm] = None
        self._init_adapter()

    def _init_adapter(self) -> None:
        try:
            from .adapter import SACAdapter, SB3AdapterConfig
            self._adapter = SACAdapter(config=self._config, adapter_config=SB3AdapterConfig())
        except Exception as e:
            logger.warning("SAC adapter init failed: %s", e)
            from .adapter import _HeuristicPolicy
            self._adapter = _HeuristicPolicy(self._config)

    def select_action(self, state: np.ndarray, deterministic: bool = False) -> np.ndarray:
        """Alias for act()."""
        return self.act(state, deterministic)

    def act(self, state: np.ndarray, deterministic: bool = False) -> np.ndarray:
        if self._adapter is not None:
            return self._adapter.act(state, deterministic)
        return np.random.randn(1)

    def update(self, experience: RLExperience) -> Dict[str, float]:
        if self._adapter is not None:
            return self._adapter.update(experience)
        return {"policy_loss": 0.0, "q1_loss": 0.0, "q2_loss": 0.0}

    def save(self, path: str) -> None:
        if self._adapter is not None:
            self._adapter.save(path)
        logger.info("SAC saved to %s", path)

    def load(self, path: str) -> None:
        if self._adapter is not None:
            self._adapter.load(path)
        logger.info("SAC loaded from %s", path)
