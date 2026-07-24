# Copyright (c) Ultrone Contributors. All rights reserved.
"""Emergent swarm coordination using local rules."""

from __future__ import annotations

import logging
import numpy as np
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from .base import BaseCoordinator, CoordinationConfig

logger = logging.getLogger("Ultrone.Brain.Reasoning.Coordination.Swarm")


@dataclass
class SwarmConfig(CoordinationConfig):
    """Configuration for swarm coordination."""
    separation_weight: float = 1.5
    alignment_weight: float = 1.0
    cohesion_weight: float = 1.0
    perception_radius: float = 50.0


class SwarmCoordination(BaseCoordinator):
    """Emergent swarm coordination using Boids-like rules.

    Agents follow three local rules: separation (avoid crowding),
    alignment (steer towards average heading), and cohesion
    (steer towards average position).
    """

    def __init__(self, config: Optional[SwarmConfig] = None):
        super().__init__(config or SwarmConfig())
        self._config: SwarmConfig = self.config  # type: ignore
        self._positions: Dict[str, np.ndarray] = {}
        self._velocities: Dict[str, np.ndarray] = {}

    def set_agent_state(self, agent_id: str, position: np.ndarray, velocity: np.ndarray) -> None:
        self._positions[agent_id] = position
        self._velocities[agent_id] = velocity

    def coordinate(self, context: Dict[str, Any]) -> Dict[str, Any]:
        new_velocities = {}
        for aid in self._agents:
            if aid not in self._positions:
                continue
            pos = self._positions[aid]
            vel = self._velocities.get(aid, np.zeros(2))
            separation = np.zeros(2)
            alignment = np.zeros(2)
            cohesion = np.zeros(2)
            neighbors = 0
            for other in self._agents:
                if other == aid or other not in self._positions:
                    continue
                other_pos = self._positions[other]
                dist = np.linalg.norm(pos - other_pos)
                if 0 < dist < self._config.perception_radius:
                    separation -= (other_pos - pos) / (dist + 1e-6)
                    alignment += self._velocities.get(other, np.zeros(2))
                    cohesion += other_pos
                    neighbors += 1
            if neighbors > 0:
                alignment /= neighbors
                cohesion = (cohesion / neighbors - pos)
            new_vel = (vel + self._config.separation_weight * separation +
                       self._config.alignment_weight * alignment +
                       self._config.cohesion_weight * cohesion)
            new_velocities[aid] = new_vel
            self._velocities[aid] = new_vel
            self._positions[aid] = pos + new_vel * 0.1
        return {"velocities": {k: v.tolist() for k, v in new_velocities.items()},
                "positions": {k: v.tolist() for k, v in self._positions.items()}}

    def get_stats(self) -> Dict[str, Any]:
        return {"type": "SwarmCoordination", "num_agents": len(self._agents)}