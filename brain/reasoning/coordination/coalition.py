# Copyright (c) Ultrone Contributors. All rights reserved.
"""Dynamic coalition formation for multi-agent cooperation."""

from __future__ import annotations

import logging
import numpy as np
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from .base import BaseCoordinator, CoordinationConfig

logger = logging.getLogger("Ultrone.Brain.Reasoning.Coordination.Coalition")


@dataclass
class CoalitionConfig(CoordinationConfig):
    """Configuration for coalition formation."""
    min_coalition_size: int = 2
    max_coalition_size: int = 5
    formation_method: str = "greedy"


class CoalitionFormation(BaseCoordinator):
    """Dynamic coalition formation for multi-agent cooperation."""

    def __init__(self, config: Optional[CoalitionConfig] = None):
        super().__init__(config or CoalitionConfig())

    def coordinate(self, context: Dict[str, Any]) -> Dict[str, Any]:
        agents = list(self._agents.keys())
        np.random.shuffle(agents)
        coalitions = []
        for i in range(0, len(agents), self._config.max_coalition_size):
            coalition = agents[i:i + self._config.max_coalition_size]
            if len(coalition) >= self._config.min_coalition_size:
                coalitions.append(coalition)
        return {"coalitions": coalitions, "num_coalitions": len(coalitions)}

    def get_stats(self) -> Dict[str, Any]:
        return {"type": "CoalitionFormation"}