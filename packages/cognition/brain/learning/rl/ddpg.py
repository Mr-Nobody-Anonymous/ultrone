# Copyright (c) Ultrone Contributors. All rights reserved.
"""Deep Deterministic Policy Gradient (DDPG) algorithm.

DDPG is an off-policy actor-critic algorithm for continuous action spaces,
combining DPG with DQN-style experience replay and target networks.
"""

from __future__ import annotations

import logging
import numpy as np
from dataclasses import dataclass
from typing import Any, Dict, Optional

from .base import BaseRLAlgorithm, RLConfig, RLExperience

logger = logging.getLogger("Ultrone.Brain.Learning.RL.DDPG")


@dataclass
class DDPGConfig(RLConfig):
    """Configuration for DDPG algorithm."""
    exploration_noise: float = 0.1
    hidden_dim: int = 256


class DDPG(BaseRLAlgorithm):
    """Deep Deterministic Policy Gradient implementation.

    Delegates to Stable-Baselines3 when available, falling back
    to heuristic policy otherwise.
    """

    def __init__(self, config: Optional[DDPGConfig] = None):
        super().__init__(config or DDPGConfig())
        self._adapter: Optional[BaseRLAlgorithm] = None
        self._init_adapter()

    def _init_adapter(self) -> None:
        """Initialize the SB3 adapter (lazy)."""
        try:
            from .adapter import DDPGAdapter, SB3AdapterConfig
            self._adapter = DDPGAdapter(config=self.config, adapter_config=SB3AdapterConfig())
        except Exception as e:
            logger.warning("DDPG adapter init failed: %s", e)
            from .adapter import _HeuristicPolicy
            self._adapter = _HeuristicPolicy(self.config)

    def act(self, state: np.ndarray, deterministic: bool = False) -> np.ndarray:
        if self._adapter is not None:
            return self._adapter.act(state, deterministic)
        return np.random.randn(1)

    def update(self, experience: RLExperience) -> Dict[str, float]:
        if self._adapter is not None:
            return self._adapter.update(experience)
        return {"actor_loss": 0.0, "critic_loss": 0.0}

    def save(self, path: str) -> None:
        if self._adapter is not None:
            self._adapter.save(path)
        logger.info("DDPG saved to %s", path)

    def load(self, path: str) -> None:
        if self._adapter is not None:
            self._adapter.load(path)
        logger.info("DDPG loaded from %s", path)

