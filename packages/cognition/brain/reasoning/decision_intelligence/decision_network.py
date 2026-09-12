"""Decision networks (influence diagrams) for structured decision analysis."""

from __future__ import annotations

import logging
import numpy as np
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple

logger = logging.getLogger("Ultrone.Brain.Reasoning.DecisionIntelligence.DecisionNetwork")


@dataclass
class DNConfig:
    """Configuration for decision networks."""
    discount_factor: float = 0.95
    num_actions: int = 5
    utility_noise: float = 0.01
    max_depth: int = 10


@dataclass
class DecisionNode:
    """A decision node representing a choice point."""
    name: str
    actions: List[str] = field(default_factory=list)
    selected_action: Optional[str] = None


@dataclass
class ChanceNode:
    """A chance (random) node representing uncertainty."""
    name: str
    outcomes: Dict[str, float] = field(default_factory=dict)
    observed_outcome: Optional[str] = None


@dataclass
class UtilityNode:
    """A utility node representing preferences over outcomes."""
    name: str
    utility_function: Optional[Callable] = None
    value: float = 0.0


class DecisionNetwork:
    """Influence diagram / decision network for structured decision-making."""

    def __init__(self, config: Optional[DNConfig] = None):
        self.config = config or DNConfig()
        self._decision_nodes: Dict[str, DecisionNode] = {}
        self._chance_nodes: Dict[str, ChanceNode] = {}
        self._utility_nodes: Dict[str, UtilityNode] = {}
        self._edges: List[Tuple[str, str]] = []

    def add_decision_node(self, name: str, actions: List[str]) -> DecisionNode:
        """Add a decision node with available actions."""
        node = DecisionNode(name=name, actions=actions)
        self._decision_nodes[name] = node
        return node

    def add_chance_node(self, name: str, outcomes: Optional[Dict[str, float]] = None) -> ChanceNode:
        """Add a chance node with possible outcomes and probabilities."""
        node = ChanceNode(name=name, outcomes=outcomes or {})
        self._chance_nodes[name] = node
        return node

    def add_utility_node(self, name: str,
                         utility_fn: Optional[Callable] = None) -> UtilityNode:
        """Add a utility node with an optional utility function."""
        node = UtilityNode(name=name, utility_function=utility_fn)
        self._utility_nodes[name] = node
        return node

    def add_edge(self, from_node: str, to_node: str) -> None:
        """Add a directed edge between nodes."""
        self._edges.append((from_node, to_node))

    def evaluate(self, state: Dict[str, Any]) -> Tuple[str, float]:
        """Evaluate the decision network and return best action and expected utility."""
        best_action = None
        best_utility = float("-inf")

        for dname, dnode in self._decision_nodes.items():
            for action in dnode.actions:
                expected_value = self._compute_expected_utility(
                    action, state, set()
                )
                if expected_value > best_utility:
                    best_utility = expected_value
                    best_action = action
                dnode.selected_action = action

        if best_action:
            for dnode in self._decision_nodes.values():
                dnode.selected_action = best_action

        return best_action, best_utility

    def _compute_expected_utility(self, action: str, state: Dict[str, Any],
                                   visited: set) -> float:
        """Recursively compute expected utility for an action."""
        total_utility = 0.0

        for uname, unode in self._utility_nodes.items():
            if unode.utility_function:
                total_utility += unode.utility_function(state | {"action": action})
            else:
                total_utility += state.get(uname, 0.0)

        for cname, cnode in self._chance_nodes.items():
            if cname in visited:
                continue
            visited.add(cname)
            for outcome, prob in cnode.outcomes.items():
                new_state = dict(state)
                new_state[cname] = outcome
                total_utility += prob * self._compute_expected_utility(
                    action, new_state, visited
                )

        noise = np.random.randn() * self.config.utility_noise
        return total_utility + noise

    def get_optimal_policy(self, state: Dict[str, Any]) -> Dict[str, str]:
        """Get the optimal policy mapping decision nodes to actions."""
        policy = {}
        for dname, dnode in self._decision_nodes.items():
            best_action, _ = self.evaluate(state)
            if best_action:
                policy[dname] = best_action
        return policy

    def reset(self) -> None:
        """Reset all nodes to initial state."""
        for node in self._decision_nodes.values():
            node.selected_action = None
        for node in self._chance_nodes.values():
            node.observed_outcome = None
        for node in self._utility_nodes.values():
            node.value = 0.0

