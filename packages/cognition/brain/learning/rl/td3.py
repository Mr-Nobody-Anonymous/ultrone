# Copyright (c) Ultrone Contributors. All rights reserved.
"""Twin Delayed DDPG (TD3) algorithm.

TD3 addresses DDPG's overestimation bias by using twin Q-networks,
delayed policy updates, and target policy smoothing.
"""

from __future__ import annotations

import logging
import numpy as np
from dataclasses import dataclass
from typing import Any, Dict, Optional

from .base import BaseRLAlgorithm, RLConfig, RLExperience

logger = logging.getLogger("Ultrone.Brain.Learning.RL.TD3")


@dataclass
class TD3Config(RLConfig):
    """Configuration for TD3 algorithm."""
    policy_delay: int = 2
    target_noise: float = 0.2
    noise_clip: float = 0.5
    exploration_noise: float = 0.1
    hidden_dim: int = 256


class TD3(BaseRLAlgorithm):
    """Twin Delayed DDPG implementation.

    Delegates to Stable-Baselines3 when available, falling back
    to heuristic policy otherwise.
    """

    def __init__(self, config: Optional[TD3Config] = None):
        super().__init__(config or TD3Config())
        self._config: TD3Config = self.config  # type: ignore
        self._adapter: Optional[BaseRLAlgorithm] = None
        self._init_adapter()

    def _init_adapter(self) -> None:
        """Initialize the SB3 adapter (lazy)."""
        try:
            from .adapter import TD3Adapter, SB3AdapterConfig
            self._adapter = TD3Adapter(config=self._config, adapter_config=SB3AdapterConfig())
        except Exception as e:
            logger.warning("TD3 adapter init failed: %s", e)
            from .adapter import _HeuristicPolicy
            self._adapter = _HeuristicPolicy(self._config)

    def act(self, state: np.ndarray, deterministic: bool = False) -> np.ndarray:
        if self._adapter is not None:
            return self._adapter.act(state, deterministic)
        return np.random.randn(1)

    def update(self, experience: RLExperience) -> Dict[str, float]:
        if self._adapter is not None:
            return self._adapter.update(experience)
        return {"actor_loss": 0.0, "critic1_loss": 0.0, "critic2_loss": 0.0}

    def save(self, path: str) -> None:
        if self._adapter is not None:
            self._adapter.save(path)
        logger.info("TD3 saved to %s", path)

    def load(self, path: str) -> None:
        if self._adapter is not None:
            self._adapter.load(path)
        logger.info("TD3 loaded from %s", path)

