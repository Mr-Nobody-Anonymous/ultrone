# Copyright (c) Ultrone Contributors. All rights reserved.
"""Monte Carlo Tree Search (MCTS) planner.

MCTS builds a search tree asymmetrically, focusing on promising
branches using Upper Confidence Bounds (UCT).  It is an *anytime*
algorithm: the more iterations, the better the plan.

Integration
-----------
Plugs into :class:`~brain.reasoning.tactical_engine.TacticalEngine`
as any other :class:`Planner` implementation.
"""

from __future__ import annotations

import logging
import math
import random
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple

from .base import Planner, PlanningAction, PlanningDomain, PlanningGoal, PlanningResult

logger = logging.getLogger("Ultrone.Brain.Reasoning.Search.MCTS")


@dataclass
class MCTSConfig:
    """Configuration for MCTS.

    Attributes
    ----------
    uct_c:
        Exploration constant for UCT (higher = more exploration).
    max_iterations:
        Number of MCTS iterations before returning best plan.
    rollout_depth:
        Maximum depth of random rollouts.
    num_simulations:
        Alias for max_iterations (test compatibility).
    max_depth:
        Alias for rollout_depth (test compatibility).
    """
    uct_c: float = math.sqrt(2)
    max_iterations: int = 1000
    rollout_depth: int = 20
    num_simulations: Optional[int] = None
    max_depth: Optional[int] = None

    def __post_init__(self):
        if self.num_simulations is not None:
            self.max_iterations = self.num_simulations
        if self.max_depth is not None:
            self.rollout_depth = self.max_depth


class _MCTSNode:
    """Node in the MCTS search tree."""

    def __init__(self, state: Any, parent: Optional["_MCTSNode"] = None, action: Optional[PlanningAction] = None):
        self.state = state
        self.parent = parent
        self.action = action
        self.children: List["_MCTSNode"] = []
        self.visits: int = 0
        self.total_value: float = 0.0
        self.untried_actions: List[PlanningAction] = []

    @property
    def is_fully_expanded(self) -> bool:
        return len(self.untried_actions) == 0

    @property
    def is_terminal(self) -> bool:
        return False  # domain-dependent; override via goal_check

    @property
    def ucb_score(self) -> float:
        if self.visits == 0:
            return float("inf")
        exploitation = self.total_value / self.visits
        exploration = math.sqrt(2.0 * math.log(self.parent.visits) / self.visits) if self.parent else 0.0
        return exploitation + exploration


class MCTS(Planner):
    """Monte Carlo Tree Search planner.

    Parameters
    ----------
    config:
        Hyper-parameters (see :class:`MCTSConfig`).
    """

    def __init__(self, config: Optional[MCTSConfig] = None) -> None:
        super().__init__()
        self.config = config or MCTSConfig()
        self._rollout_fn: Optional[Callable] = None
        self._transition_fn: Optional[Callable] = None

    def initialize(self, domain: PlanningDomain) -> None:
        super().initialize(domain)
        self._rollout_fn = domain.heuristic_fn
        self._transition_fn = domain.action_cost_fn

    def _select(self, node: _MCTSNode) -> _MCTSNode:
        """Select best child using UCT."""
        while node.is_fully_expanded and not node.is_terminal:
            if not node.children:
                return node
            node = max(node.children, key=lambda c: c.ucb_score)
        return node

    def _expand(self, node: _MCTSNode) -> Optional[_MCTSNode]:
        """Expand one untried action."""
        if not node.untried_actions:
            return None
        action = node.untried_actions.pop()
        next_state = self._transition(state=node.state, action=action) if self._transition_fn else node.state
        child = _MCTSNode(state=next_state, parent=node, action=action)
        node.children.append(child)
        return child

    def _transition(self, state: Any, action: PlanningAction) -> Any:
        """Apply action to get next state (for grid-based domains)."""
        if isinstance(state, tuple) and len(state) == 2:
            x, y = state
            dx = action.parameters.get("dx", 0)
            dy = action.parameters.get("dy", 0)
            return (x + dx, y + dy)
        return state

    def _simulate(self, state: Any, depth: int) -> float:
        """Run random rollout from state."""
        if self._rollout_fn:
            return self._rollout_fn(state, None)
        return random.random()

    def _backpropagate(self, node: _MCTSNode, value: float) -> None:
        """Propagate value up the tree."""
        while node:
            node.visits += 1
            node.total_value += value
            node = node.parent

    def plan(self, state: Any, goal: PlanningGoal) -> PlanningResult:
        domain = self._domain
        if domain is None:
            raise RuntimeError("MCTS not initialised — call .initialize() first.")

        target = goal.target_state if goal.target_state is not None else state
        root = _MCTSNode(state=state)
        root.untried_actions = list(domain.discrete_actions)

        for _ in range(self.config.max_iterations):
            # Selection
            node = self._select(root)

            # Expansion
            if not node.is_terminal and node.untried_actions:
                child = self._expand(node)
                if child:
                    node = child

            # Simulation
            value = self._simulate(node.state, self.config.rollout_depth)

            # Backpropagation
            self._backpropagate(node, value)

        # Extract best action sequence
        best_path: List[PlanningAction] = []
        node = root
        while node.children:
            best_child = max(node.children, key=lambda c: c.visits)
            if best_child.action:
                best_path.append(best_child.action)
            node = best_child

        total_cost = len(best_path)
        result = PlanningResult(
            success=len(best_path) > 0,
            actions=best_path,
            cost=total_cost,
            nodes_expanded=root.visits,
            plan_length=len(best_path),
            metadata={"root_visits": root.visits},
        )
        logger.info("MCTS plan found: len=%d, cost=%.2f", result.plan_length, result.cost)
        return self._record_result(result)
