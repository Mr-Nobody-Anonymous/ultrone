"""Logistics model for battlefield simulation."""

from __future__ import annotations

import logging
import numpy as np
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from .base import WorldModel, WorldModelConfig

logger = logging.getLogger("Ultrone.Sim.WorldModeling.Logistics")


@dataclass
class LogisticsConfig(WorldModelConfig):
    """Configuration for logistics model."""
    supply_chain_length: int = 5
    resupply_rate: float = 10.0
    convoy_speed: float = 5.0


class LogisticsModel(WorldModel):
    """Logistics and supply chain model.

    Simulates supply convoys, resupply operations, and logistics
    constraints that affect military operations.
    """

    def __init__(self, config: Optional[LogisticsConfig] = None):
        super().__init__(config or LogisticsConfig())
        self._supply_level: float = 100.0
        self._convoys_active: int = 0
        self._supplies_delivered: float = 0.0

    def update(self, dt: float) -> None:
        """Advance logistics by one time step."""
        self._tick += 1
        # Natural resupply
        self._supply_level = min(100.0, self._supply_level + self.config.resupply_rate * 0.01)
        # Active convoys
        if self._tick % 10 == 0:
            self._convoys_active = max(0, self._convoys_active + np.random.randint(-1, 2))

    def dispatch_convoy(self) -> bool:
        """Dispatch a supply convoy."""
        self._convoys_active += 1
        return True

    def get_state(self) -> Dict[str, Any]:
        return {
            "supply_level": self._supply_level,
            "convoys_active": self._convoys_active,
            "supplies_delivered": self._supplies_delivered,
        }
