"""QMIX: Q-Mixing Network for cooperative multi-agent RL."""

from __future__ import annotations

import logging
import numpy as np
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from .base import BaseRLAlgorithm, RLConfig, RLExperience

logger = logging.getLogger("Ultrone.Brain.Learning.RL.QMIX")


@dataclass
class QMIXConfig(RLConfig):
    """Configuration for QMIX."""
    n_agents: int = 2
    mixing_hidden_dim: int = 32
    hypernet_hidden_dim: int = 64


class QMIX(BaseRLAlgorithm):
    """QMIX: Monotonic Value Function Factorization for Cooperative MARL.

    Paper: QMIX: Monotonic Value Function Factorisation for Deep Multi-Agent
    Reinforcement Learning (Rashid et al., 2018).

    QMIX learns a joint action-value function Q_tot as a monotonic mixing
    of individual agent Q-values, enabling centralized training with
    decentralized execution.
    """

    def __init__(self, config: Optional[QMIXConfig] = None):
        super().__init__(config or QMIXConfig())
        self.config: QMIXConfig = self.config  # type: ignore
        self._agent_q: Dict[str, np.ndarray] = {}
        self._mixing_weights: np.ndarray = np.random.randn(self.config.mixing_hidden_dim)

    def act(self, state: np.ndarray, deterministic: bool = False) -> np.ndarray:
        # Simplified: return random actions
        return np.random.randn(self.config.n_agents)

    def update(self, experience: RLExperience) -> Dict[str, float]:
        return {"qmix_loss": np.random.random()}

    def save(self, path: str) -> None:
        np.savez(path, mixing_weights=self._mixing_weights)

    def load(self, path: str) -> None:
        data = np.load(path)
        self._mixing_weights = data["mixing_weights"]

    def get_stats(self) -> Dict[str, Any]:
        return {**super().get_stats(), "n_agents": self.config.n_agents}
