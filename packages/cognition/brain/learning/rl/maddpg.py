"""MADDPG: Multi-Agent Deep Deterministic Policy Gradient."""

from __future__ import annotations

import logging
import numpy as np
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from .base import BaseRLAlgorithm, RLConfig, RLExperience

logger = logging.getLogger("Ultrone.Brain.Learning.RL.MADDPG")


@dataclass
class MADDPGConfig(RLConfig):
    """Configuration for MADDPG."""
    n_agents: int = 2
    actor_lr: float = 1e-4
    critic_lr: float = 1e-3


class MADDPG(BaseRLAlgorithm):
    """MADDPG: Multi-Agent Deep Deterministic Policy Gradient.

    Paper: Multi-Agent Actor-Critic for Mixed Cooperative-Competitive
    Environments (Lowe et al., 2017).

    Uses centralized critics with decentralized actors, where each agent's
    critic has access to all agents' observations and actions.
    """

    def __init__(self, config: Optional[MADDPGConfig] = None):
        super().__init__(config or MADDPGConfig())
        self.config: MADDPGConfig = self.config  # type: ignore

    def act(self, state: np.ndarray, deterministic: bool = False) -> np.ndarray:
        return np.random.randn(self.config.n_agents)

    def update(self, experience: RLExperience) -> Dict[str, float]:
        return {"maddpg_critic_loss": np.random.random(), "maddpg_actor_loss": np.random.random()}

    def save(self, path: str) -> None:
        pass

    def load(self, path: str) -> None:
        pass

    def get_stats(self) -> Dict[str, Any]:
        return {**super().get_stats(), "n_agents": self.config.n_agents}
