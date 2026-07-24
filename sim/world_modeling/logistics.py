"""Supply chain and logistics simulation."""

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
    num_supply_routes: int = 5
    supply_delay_ticks: int = 10


class LogisticsModel(WorldModel):
    """Supply chain and logistics simulation.

    Manages supply routes between depots and forward operating
    bases, with convoy simulation and disruption events.
    """

    def __init__(self, config: Optional[LogisticsConfig] = None):
        super().__init__(config or LogisticsConfig())
        self._routes: Dict[str, Dict[str, Any]] = {}
        self._convoys: List[Dict[str, Any]] = []

    def initialize(self) -> None:
        for i in range(self.config.num_supply_routes):
            self._routes[f"route_{i}"] = {
                "origin": (np.random.randint(0, 100), np.random.randint(0, 100)),
                "destination": (np.random.randint(0, 100), np.random.randint(0, 100)),
                "active": True,
                "capacity": 100.0,
                "transit_time": self.config.supply_delay_ticks,
            }

    def update(self, dt: float) -> None:
        self._tick += 1
        # Move convoys along routes
        for convoy in self._convoys[:]:
            convoy["progress"] += 1
            if convoy["progress"] >= convoy["transit_time"]:
                self._convoys.remove(convoy)
                logger.debug("Convoy arrived: %s", convoy["id"])

    def request_supply(self, destination: Tuple[int, int], amount: float) -> str:
        """Request a supply convoy. Returns convoy ID."""
        convoy_id = f"convoy_{len(self._convoys) + 1}"
        self._convoys.append({
            "id": convoy_id,
            "destination": destination,
            "amount": amount,
            "progress": 0,
            "transit_time": self.config.supply_delay_ticks,
        })
        return convoy_id

    def get_state(self) -> Dict[str, Any]:
        return {
            "routes": dict(self._routes),
            "active_convoys": len(self._convoys),
        }

