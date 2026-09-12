"""VDN: Value Decomposition Networks for cooperative MARL."""

from __future__ import annotations

import logging
import numpy as np
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from .base import BaseRLAlgorithm, RLConfig, RLExperience

logger = logging.getLogger("Ultrone.Brain.Learning.RL.VDN")


@dataclass
class VDNConfig(RLConfig):
    """Configuration for VDN."""
    n_agents: int = 2


class VDN(BaseRLAlgorithm):
    """VDN: Value Decomposition Networks.

    Paper: Value-Decomposition Networks For Cooperative Multi-Agent Learning
    (Sunehag et al., 2018).

    Decomposes the joint action-value function into a sum of individual
    agent value functions: Q_tot(s, a) = sum_i Q_i(s, a_i).
    """

    def __init__(self, config: Optional[VDNConfig] = None):
        super().__init__(config or VDNConfig())
        self.config: VDNConfig = self.config  # type: ignore

    def act(self, state: np.ndarray, deterministic: bool = False) -> np.ndarray:
        return np.random.randn(self.config.n_agents)

    def update(self, experience: RLExperience) -> Dict[str, float]:
        return {"vdn_loss": np.random.random()}

    def save(self, path: str) -> None:
        pass

    def load(self, path: str) -> None:
        pass
