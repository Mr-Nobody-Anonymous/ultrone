"""Temporal influence diagrams for dynamic decision analysis over time."""

from __future__ import annotations

import logging
import numpy as np
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("Ultrone.Brain.Reasoning.DecisionIntelligence.DynamicInfluenceGraph")


@dataclass
class DIGConfig:
    """Configuration for dynamic influence graphs."""
    time_horizon: int = 10
    discount_factor: float = 0.95
    num_simulations: int = 100
    influence_threshold: float = 0.1
    state_dim: int = 8


@dataclass
class InfluenceNode:
    """A node in the dynamic influence graph."""
    name: str
    value: float = 0.0
    parents: List[str] = field(default_factory=list)
    children: List[str] = field(default_factory=list)
    influence_weight: float = 1.0


@dataclass
class TemporalInfluence:
    """Temporal influence between two nodes over time."""
    source: str
    target: str
    influence_values: List[float] = field(default_factory=list)
    time_lag: int = 1


class DynamicInfluenceGraph:
    """Models dynamic influence relationships that evolve over time."""

    def __init__(self, config: Optional[DIGConfig] = None):
        self.config = config or DIGConfig()
        self._nodes: Dict[str, InfluenceNode] = {}
        self._influences: List[TemporalInfluence] = []
        self._time_step: int = 0

    def add_node(self, name: str, initial_value: float = 0.0,
                 influence_weight: float = 1.0) -> InfluenceNode:
        """Add a new node to the influence graph."""
        node = InfluenceNode(
            name=name,
            value=initial_value,
            influence_weight=influence_weight,
        )
        self._nodes[name] = node
        return node

    def add_influence(self, source: str, target: str, time_lag: int = 1,
                      weight: float = 1.0) -> None:
        """Add a directed influence relationship."""
        if source in self._nodes and target in self._nodes:
            self._nodes[source].children.append(target)
            self._nodes[target].parents.append(source)
            self._influences.append(TemporalInfluence(
                source=source, target=target, time_lag=time_lag
            ))

    def step(self, external_forces: Optional[Dict[str, float]] = None) -> Dict[str, float]:
        """Advance the influence graph by one time step."""
        self._time_step += 1
        new_values = {}

        for name, node in self._nodes.items():
            parent_influence = 0.0
            for parent_name in node.parents:
                parent = self._nodes[parent_name]
                influence = self._find_influence(parent_name, name)
                lag = influence.time_lag if influence else 1
                if self._time_step > lag:
                    parent_influence += parent.value * (influence.influence_weight if influence else 1.0)

            external = external_forces.get(name, 0.0) if external_forces else 0.0
            noise = np.random.randn() * 0.01
            new_values[name] = (node.value * self.config.discount_factor
                                + parent_influence + external + noise)

        for name, val in new_values.items():
            self._nodes[name].value = val

        return new_values

    def get_influence_matrix(self) -> np.ndarray:
        """Get the adjacency matrix of influence weights."""
        names = list(self._nodes.keys())
        n = len(names)
        matrix = np.zeros((n, n))
        for infl in self._influences:
            i = names.index(infl.source)
            j = names.index(infl.target)
            matrix[i, j] = 1.0
        return matrix

    def identify_key_influencers(self) -> List[Tuple[str, float]]:
        """Identify nodes with the highest outgoing influence."""
        influencers = []
        for name, node in self._nodes.items():
            total_influence = sum(
                infl.influence_weight
                for infl in self._influences
                if infl.source == name
            )
            influencers.append((name, total_influence))
        influencers.sort(key=lambda x: x[1], reverse=True)
        return influencers

    def reset(self) -> None:
        """Reset the influence graph to initial state."""
        self._time_step = 0
        for node in self._nodes.values():
            node.value = 0.0

    def _find_influence(self, source: str, target: str) -> Optional[TemporalInfluence]:
        for infl in self._influences:
            if infl.source == source and infl.target == target:
                return infl
        return None

    @property
    def num_nodes(self) -> int:
        return len(self._nodes)

    @property
    def time_step(self) -> int:
        return self._time_step

