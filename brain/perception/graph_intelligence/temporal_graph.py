# Copyright (c) Ultrone Contributors. All rights reserved.
"""Temporal graph analysis for dynamic networks."""

from __future__ import annotations

import logging
import numpy as np
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Union

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

    def analyze(self, snapshots: List[np.ndarray]) -> Dict[str, Any]:
        """Analyze temporal graph snapshots.
        
        Args:
            snapshots: List of adjacency matrices representing graph snapshots over time.
            
        Returns:
            Dict with analysis results including temporal centrality, 
            graph evolution metrics, and change points.
        """
        if not snapshots:
            return {"error": "no_snapshots"}
        
        # Store snapshots
        for s in snapshots:
            self.add_snapshot(s)
        
        # Compute temporal centrality
        centrality = self.compute_temporal_centrality()
        
        # Compute graph evolution metrics
        num_nodes = snapshots[0].shape[0] if snapshots else 0
        edge_counts = []
        for adj in snapshots:
            edge_counts.append(int(np.sum(adj) / 2))  # undirected
        
        return {
            "temporal_centrality": centrality.tolist() if len(centrality) > 0 else [],
            "num_snapshots": len(snapshots),
            "num_nodes": num_nodes,
            "edge_counts": edge_counts,
            "mean_edges": float(np.mean(edge_counts)) if edge_counts else 0.0,
        }

    def compute_temporal_centrality(self) -> np.ndarray:
        if not self._snapshots:
            return np.array([])
        centrality = np.zeros(self._snapshots[0].shape[0])
        for adj in self._snapshots:
            centrality += adj.sum(axis=1)
        return centrality / len(self._snapshots)

    def get_stats(self) -> Dict[str, Any]:
        return {"type": "TemporalGraph", "snapshots": len(self._snapshots)}
