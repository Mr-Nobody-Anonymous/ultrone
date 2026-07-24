# Copyright (c) Ultrone Contributors. All rights reserved.
"""Temporal graph analysis for dynamic networks."""

from __future__ import annotations

import logging
import numpy as np
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

logger = logging.getLogger("Ultrone.Brain.Perception.GraphIntelligence.Temporal")


@dataclass
class TemporalGraphConfig:
    """Configuration for temporal graph analysis."""
    window_size: int = 10
    stride: int = 1


class TemporalGraph:
    """Temporal graph analysis for evolving networks."""

    def __init__(self, config: Optional[TemporalGraphConfig] = None):
        self.config = config or TemporalGraphConfig()
        self._snapshots: List[np.ndarray] = []

    def add_snapshot(self, adjacency: np.ndarray) -> None:
        self._snapshots.append(adjacency)
        if len(self._snapshots) > self.config.window_size:
            self._snapshots.pop(0)

    def compute_temporal_centrality(self) -> np.ndarray:
        if not self._snapshots:
            return np.array([])
        centrality = np.zeros(self._snapshots[0].shape[0])
        for adj in self._snapshots:
            centrality += adj.sum(axis=1)
        return centrality / len(self._snapshots)

    def get_stats(self) -> Dict[str, Any]:
        return {"type": "TemporalGraph", "snapshots": len(self._snapshots)}