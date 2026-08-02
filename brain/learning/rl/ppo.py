# Copyright (c) Ultrone Contributors. All rights reserved.
"""Proximal Policy Optimization (PPO) algorithm.

PPO is a policy gradient method that uses a clipped surrogate objective
to constrain policy updates, providing stable training with good sample
efficiency. Integrates with the BaseRLAlgorithm interface.
"""

from __future__ import annotations

import logging
import numpy as np
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .base import BaseRLAlgorithm, RLConfig, RLExperience

logger = logging.getLogger("Ultrone.Brain.Learning.RL.PPO")


@dataclass
class PPOConfig(RLConfig):
    """Configuration for PPO algorithm."""
    clip_epsilon: float = 0.2
    entropy_coef: float = 0.01
    value_coef: float = 0.5
    max_grad_norm: float = 0.5
    ppo_epochs: int = 10
    gae_lambda: float = 0.95
    hidden_dim: int = 256
    num_layers: int = 2


class PPO(BaseRLAlgorithm):
    """Proximal Policy Optimization implementation.

    Uses a clipped surrogate objective with Generalized Advantage Estimation
    for stable and sample-efficient policy optimization.

    This implementation delegates to Stable-Baselines3 when available,
    falling back to a heuristic policy otherwise.
    """

    def __init__(self, config: Optional[PPOConfig] = None):
        super().__init__(config or PPOConfig())
        self._config: PPOConfig = self.config  # type: ignore
        self._adapter: Optional[BaseRLAlgorithm] = None
        self._init_adapter()

    def _init_adapter(self) -> None:
        """Initialize the SB3 adapter (lazy)."""
        try:
            from .adapter import PPOAdapter, SB3AdapterConfig
            adapter_cfg = SB3AdapterConfig(
                policy_kwargs={
                    "net_arch": {
                        "pi": [self._config.hidden_dim] * self._config.num_layers,
                        "vf": [self._config.hidden_dim] * self._config.num_layers
                    },
                },
            )
            self._adapter = PPOAdapter(config=self._config, adapter_config=adapter_cfg)
        except Exception as e:
            logger.warning("PPO adapter init failed: %s", e)
            from .adapter import _HeuristicPolicy
            self._adapter = _HeuristicPolicy(self._config)

    def select_action(self, state: np.ndarray, deterministic: bool = False) -> np.ndarray:
        """Alias for act()."""
        return self.act(state, deterministic)

    def act(self, state: np.ndarray, deterministic: bool = False) -> np.ndarray:
        """Sample action from policy network via SB3."""
        if self._adapter is not None:
            return self._adapter.act(state, deterministic)
        return np.random.randn(1)

    def update(self, experience: RLExperience) -> Dict[str, float]:
        """Update policy using PPO clipped objective (delegated to SB3)."""
        if self._adapter is not None:
            return self._adapter.update(experience)
        return {"policy_loss": 0.0, "value_loss": 0.0, "entropy": 0.0}

    def save(self, path: str) -> None:
        """Save model parameters via SB3."""
        if self._adapter is not None:
            self._adapter.save(path)
        logger.info("PPO saved to %s", path)

    def load(self, path: str) -> None:
        """Load model parameters from SB3 checkpoint."""
        if self._adapter is not None:
            self._adapter.load(path)
        logger.info("PPO loaded from %s", path)
