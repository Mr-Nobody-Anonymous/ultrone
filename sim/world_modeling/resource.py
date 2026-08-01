"""Resource model for battlefield simulation."""

from __future__ import annotations

import logging
import numpy as np
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from .base import WorldModel, WorldModelConfig

logger = logging.getLogger("Ultrone.Sim.WorldModeling.Resource")


@dataclass
class ResourceConfig(WorldModelConfig):
    """Configuration for resource model."""
    initial_fuel: float = 1000.0
    initial_ammo: float = 500.0
    fuel_consumption_rate: float = 0.1
    ammo_consumption_rate: float = 0.05


class ResourceModel(WorldModel):
    """Resource model tracking fuel, ammo, and supplies.

    Simulates consumption and resupply of battlefield resources.
    """

    def __init__(self, config: Optional[ResourceConfig] = None):
        super().__init__(config or ResourceConfig())
        self._fuel: float = self.config.initial_fuel
        self._ammo: float = self.config.initial_ammo

    def update(self, dt: float) -> None:
        """Consume resources over time."""
        self._tick += 1
        self._fuel = max(0.0, self._fuel - self.config.fuel_consumption_rate)
        self._ammo = max(0.0, self._ammo - self.config.ammo_consumption_rate)

    def consume_fuel(self, amount: float) -> float:
        """Consume fuel and return actual amount consumed."""
        consumed = min(amount, self._fuel)
        self._fuel -= consumed
        return consumed

    def consume_ammo(self, amount: float) -> float:
        """Consume ammo and return actual amount consumed."""
        consumed = min(amount, self._ammo)
        self._ammo -= consumed
        return consumed

    def resupply(self, fuel: float = 0.0, ammo: float = 0.0) -> None:
        """Resupply resources."""
        self._fuel = min(self.config.initial_fuel, self._fuel + fuel)
        self._ammo = min(self.config.initial_ammo, self._ammo + ammo)

    def get_state(self) -> Dict[str, Any]:
        return {
            "fuel": self._fuel,
            "ammo": self._ammo,
            "fuel_pct": 100.0 * self._fuel / max(1.0, self.config.initial_fuel),
            "ammo_pct": 100.0 * self._ammo / max(1.0, self.config.initial_ammo),
        }
