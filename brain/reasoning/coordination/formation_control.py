# Copyright (c) Ultrone Contributors. All rights reserved.
"""Formation control for multi-agent swarms."""

from __future__ import annotations

import logging
import numpy as np
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from .base import BaseCoordinator, CoordinationConfig

logger = logging.getLogger("Ultrone.Brain.Reasoning.Coordination.Formation")


@dataclass
class FormationConfig(CoordinationConfig):
    """Configuration for formation control."""
    formation_type: str = "wedge"  # wedge, line, diamond, vee, echelon
    spacing: float = 10.0
    rigidity: float = 0.8


class FormationControl(BaseCoordinator):
    """Formation control for coordinating multi-agent movement.

    Supports wedge, line, diamond, vee, and echelon formations.
    """

    FORMATIONS = {
        "wedge": [(0, 0), (-1, 1), (1, 1), (-2, 2), (2, 2)],
        "line": [(0, 0), (0, 1), (0, 2), (0, 3), (0, 4)],
        "diamond": [(0, 0), (-1, 1), (1, 1), (0, 2)],
        "vee": [(0, 0), (-1, 1), (1, 1), (-2, 2), (2, 2)],
        "echelon": [(0, 0), (1, 1), (2, 2), (3, 3), (4, 4)],
    }

    def __init__(self, config: Optional[FormationConfig] = None):
        super().__init__(config or FormationConfig())

    def get_formation_offsets(self, num_agents: int) -> List[Tuple[float, float]]:
        base = self.FORMATIONS.get(self._config.formation_type, self.FORMATIONS["wedge"])
        return [(x * self._config.spacing, y * self._config.spacing) for x, y in base[:num_agents]]

    def coordinate(self, context: Dict[str, Any]) -> Dict[str, Any]:
        leader_pos = context.get("leader_position", (0, 0))
        num_agents = len(self._agents)
        offsets = self.get_formation_offsets(num_agents)
        positions = {}
        for i, aid in enumerate(self._agents):
            if i < len(offsets):
                positions[aid] = (leader_pos[0] + offsets[i][0], leader_pos[1] + offsets[i][1])
        return {"positions": positions, "formation": self._config.formation_type}

    def get_stats(self) -> Dict[str, Any]:
        return {"type": "FormationControl", "formation": self._config.formation_type}