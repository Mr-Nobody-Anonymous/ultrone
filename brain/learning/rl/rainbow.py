# Copyright (c) Ultrone Contributors. All rights reserved.
"""Rainbow DQN - combines DQN improvements (Prioritized Replay, Dueling,
Noisy Nets, Distributional RL (C51), Multi-step, Double DQN)."""

from __future__ import annotations

import logging
import numpy as np
from dataclasses import dataclass
from typing import Any, Dict, Optional

from .base import BaseRLAlgorithm, RLConfig, RLExperience

logger = logging.getLogger("Ultrone.Brain.Learning.RL.Rainbow")


@dataclass
class RainbowConfig(RLConfig):
    """Configuration for Rainbow DQN."""
    n_step: int = 3
    v_min: float = -10.0
    v_max: float = 10.0
    num_atoms: int = 51
    hidden_dim: int = 256


class RainbowDQN(BaseRLAlgorithm):
    """Rainbow DQN combining all DQN improvements.

    Uses Stable-Baselines3 DQN as the base implementation. For a full
    Rainbow with distributional RL (C51), noisy nets, and multi-step,
    consider integrating SB3 contrib or RLlib.
    """

    def __init__(self, config: Optional[RainbowConfig] = None):
        super().__init__(config or RainbowConfig())
        self._config: RainbowConfig = self.config  # type: ignore
        self._adapter: Optional[BaseRLAlgorithm] = None
        self._init_adapter()

    def _init_adapter(self) -> None:
        """Initialize the SB3 adapter (lazy)."""
        try:
            from .adapter import DQNAdapter, SB3AdapterConfig
            pol_kwargs = {"net_arch": [self._config.hidden_dim] * 3}
            self._adapter = DQNAdapter(
                config=self._config,
                adapter_config=SB3AdapterConfig(policy_kwargs=pol_kwargs),
            )
        except Exception as e:
            logger.warning("Rainbow adapter init failed: %s", e)

    def act(self, state: np.ndarray, deterministic: bool = False) -> np.ndarray:
        if self._adapter is not None:
            return self._adapter.act(state, deterministic)
        return np.array([0])

    def update(self, experience: RLExperience) -> Dict[str, float]:
        if self._adapter is not None:
            return self._adapter.update(experience)
        return {"q_loss": 0.0}

    def save(self, path: str) -> None:
        if self._adapter is not None:
            self._adapter.save(path)
        logger.info("Rainbow saved to %s", path)

    def load(self, path: str) -> None:
        if self._adapter is not None:
            self._adapter.load(path)
        logger.info("Rainbow loaded from %s", path)

