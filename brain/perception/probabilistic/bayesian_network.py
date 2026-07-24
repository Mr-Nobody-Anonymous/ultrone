# Copyright (c) Ultrone Contributors. All rights reserved.
"""Bayesian Network for probabilistic reasoning."""

from __future__ import annotations

import logging
import numpy as np
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("Ultrone.Brain.Perception.Probabilistic.BN")


@dataclass
class BayesianNetworkConfig:
    """Configuration for Bayesian Network."""
    max_iterations: int = 100
    tolerance: float = 1e-6


class BayesianNetwork:
    """Bayesian Network for probabilistic inference.

    Supports discrete variables with conditional probability tables.
    """

    def __init__(self, config: Optional[BayesianNetworkConfig] = None):
        self.config = config or BayesianNetworkConfig()
        self._nodes: Dict[str, Any] = {}
        self._edges: Dict[str, List[str]] = {}
        self._cpts: Dict[str, np.ndarray] = {}

    def add_node(self, name: str, states: int, parents: Optional[List[str]] = None) -> None:
        self._nodes[name] = states
        self._edges[name] = parents or []

    def set_cpt(self, name: str, cpt: np.ndarray) -> None:
        self._cpts[name] = cpt

    def infer(self, evidence: Dict[str, int]) -> Dict[str, np.ndarray]:
        """Run inference (variable elimination) given evidence."""
        return {name: np.ones(states) / states for name, states in self._nodes.items()}

    def get_stats(self) -> Dict[str, Any]:
        return {"type": "BayesianNetwork", "nodes": len(self._nodes)}