"""Resource model for simulation."""

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
    num_resource_nodes: int = 20
    resource_types: List[str] = field(default_factory=lambda: ["fuel", "ammo", "food", "parts"])
    regeneration_rate: float = 0.01


class ResourceModel(WorldModel):
    """Resource distribution and depletion model.

    Manages resource nodes on the battlefield that agents
    can interact with for resupply and replenishment.
    """

    def __init__(self, config: Optional[ResourceConfig] = None):
        super().__init__(config or ResourceConfig())
        self._nodes: Dict[str, Dict[str, Any]] = {}

    def initialize(self, width: int = 100, height: int = 100) -> None:
        rng = np.random.RandomState(self.config.seed)
        for i in range(self.config.num_resource_nodes):
            node_id = f"resource_{i}"
            rtype = rng.choice(self.config.resource_types)
            self._nodes[node_id] = {
                "position": (rng.randint(0, width), rng.randint(0, height)),
                "type": rtype,
                "capacity": rng.uniform(50, 200),
                "current": rng.uniform(50, 200),
                "alive": True,
            }
        logger.info("Resource model initialized: %d nodes", len(self._nodes))

    def update(self, dt: float) -> None:
        self._tick += 1
        for node in self._nodes.values():
            if node["alive"] and node["current"] < node["capacity"]:
                node["current"] = min(node["capacity"], node["current"] + self.config.regeneration_rate * node["capacity"])

    def extract(self, node_id: str, amount: float) -> float:
        """Extract resources from a node. Returns actual amount extracted."""
        node = self._nodes.get(node_id)
        if not node or not node["alive"]:
            return 0.0
        extracted = min(amount, node["current"])
        node["current"] -= extracted
        return extracted

    def get_state(self) -> Dict[str, Any]:
        return {"nodes": {k: dict(v) for k, v in self._nodes.items()}}

