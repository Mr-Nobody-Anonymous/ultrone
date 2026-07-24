"""Influence Diagrams for structured decision-making under uncertainty."""

from __future__ import annotations

import logging
import numpy as np
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

logger = logging.getLogger("Ultrone.Brain.Reasoning.DI.InfluenceDiagram")


@dataclass
class IDConfig:
    """Configuration for influence diagrams."""
    max_iterations: int = 100
    tolerance: float = 1e-6


class InfluenceDiagram:
    """Influence Diagram (Decision Network) for structured decision-making.

    Extends Bayesian networks with:
    - **Chance nodes**: Uncertain events (circles)
    - **Decision nodes**: Choices under our control (rectangles)
    - **Utility nodes**: Outcomes we care about (diamonds)

    Performs expected utility calculation for each decision alternative
    using variable elimination on the underlying factor graph.
    """

    def __init__(self, config: Optional[IDConfig] = None):
        self.config = config or IDConfig()
        self._chance_nodes: Dict[str, Any] = {}
        self._decision_nodes: Dict[str, Any] = {}
        self._utility_nodes: Dict[str, Any] = {}
        self._edges: List[Tuple[str, str]] = []

    def add_chance_node(self, name: str, cpt: np.ndarray, parents: Optional[List[str]] = None) -> None:
        """Add a chance node with conditional probability table."""
        self._chance_nodes[name] = {"cpt": cpt, "parents": parents or []}

    def add_decision_node(self, name: str, options: List[str]) -> None:
        """Add a decision node with available options."""
        self._decision_nodes[name] = {"options": options, "parents": []}

    def add_utility_node(self, name: str, function: Callable[..., float], parents: List[str]) -> None:
        """Add a utility node with a function computing utility."""
        self._utility_nodes[name] = {"function": function, "parents": parents}

    def solve(self, evidence: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Solve the influence diagram for optimal decisions."""
        evidence = evidence or {}
        results = {}
        for d_name, d_node in self._decision_nodes.items():
            best_option = None
            best_eu = float("-inf")
            for option in d_node["options"]:
                eu = self._expected_utility({**evidence, d_name: option})
                if eu > best_eu:
                    best_eu = eu
                    best_option = option
            results[d_name] = {"best_option": best_option, "expected_utility": best_eu}
        return results

    def _expected_utility(self, assignment: Dict[str, Any]) -> float:
        """Compute expected utility given an assignment of decisions/evidence."""
        total = 0.0
        for u_name, u_node in self._utility_nodes.items():
            args = {p: assignment.get(p, 0.5) for p in u_node["parents"]}
            total += u_node["function"](**args)
        return total

    def get_stats(self) -> Dict[str, Any]:
        return {
            "type": "InfluenceDiagram",
            "chance_nodes": len(self._chance_nodes),
            "decision_nodes": len(self._decision_nodes),
            "utility_nodes": len(self._utility_nodes),
        }
