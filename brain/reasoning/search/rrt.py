"""RRT/RRT*: Rapidly-exploring Random Trees for motion planning."""

from __future__ import annotations

import logging
import numpy as np
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple

from .base import Planner, PlanningDomain, PlanningGoal, PlanningResult, PlanningAction

logger = logging.getLogger("Ultrone.Brain.Reasoning.Search.RRT")


@dataclass
class RRTConfig:
    """Configuration for RRT planning."""
    max_iterations: int = 1000
    step_size: float = 5.0
    goal_sample_rate: float = 0.1
    goal_tolerance: float = 1.0
    use_star: bool = True  # RRT* vs RRT


class RRTPlanner(Planner):
    """Rapidly-exploring Random Tree (RRT/RRT*) planner.

    RRT efficiently explores high-dimensional spaces by biasing
    growth towards unexplored regions. RRT* adds asymptotic optimality
    through rewiring of the tree.

    Use cases in ULTRONE:
    - UAV/UGV path planning through contested airspace
    - Missile trajectory optimization
    - Multi-agent coordinated movement
    """

    def __init__(self, config: Optional[RRTConfig] = None):
        super().__init__()
        self.config = config or RRTConfig()
        self._collision_fn: Optional[Callable] = None
        self._random_state_fn: Optional[Callable] = None

    def initialize(self, domain: PlanningDomain) -> None:
        super().initialize(domain)

    def plan(self, state: np.ndarray, goal: PlanningGoal) -> PlanningResult:
        """Plan a path from state to goal using RRT/RRT*."""
        start = np.array(state) if not isinstance(state, np.ndarray) else state
        goal_pos = np.array(goal.target_state) if goal.target_state is not None else start

        nodes = [start]
        parents = [-1]
        costs = [0.0]

        for i in range(self.config.max_iterations):
            # Sample with goal bias
            if np.random.random() < self.config.goal_sample_rate:
                sample = goal_pos
            else:
                sample = np.random.uniform(0, 100, size=start.shape)

            # Find nearest
            nearest_idx = np.argmin([np.linalg.norm(n - sample) for n in nodes])
            nearest = nodes[nearest_idx]

            # Steer
            direction = sample - nearest
            dist = np.linalg.norm(direction)
            if dist > self.config.step_size:
                direction = direction / dist * self.config.step_size
            new_node = nearest + direction

            # Collision check
            if self._collision_fn and self._collision_fn(new_node):
                continue

            nodes.append(new_node)
            parents.append(nearest_idx)
            costs.append(costs[nearest_idx] + np.linalg.norm(new_node - nearest))

            # RRT* rewiring
            if self.config.use_star and len(nodes) > 1:
                self._rewire(nodes, parents, costs, len(nodes) - 1)

            # Goal check
            if np.linalg.norm(new_node - goal_pos) < self.config.goal_tolerance:
                return self._extract_path(nodes, parents, len(nodes) - 1, costs[-1])

        # Return best path found
        goal_idx = np.argmin([np.linalg.norm(n - goal_pos) for n in nodes])
        return self._extract_path(nodes, parents, goal_idx, costs[goal_idx])

    def _rewire(self, nodes: List, parents: List, costs: List, new_idx: int) -> None:
        """RRT* rewiring step for asymptotic optimality."""
        new_node = nodes[new_idx]
        radius = self.config.step_size * 2
        for i in range(len(nodes) - 1):
            if i == new_idx:
                continue
            dist = np.linalg.norm(nodes[i] - new_node)
            if dist < radius:
                new_cost = costs[new_idx] + dist
                if new_cost < costs[i]:
                    costs[i] = new_cost
                    parents[i] = new_idx

    def _extract_path(self, nodes: List, parents: List, idx: int, cost: float) -> PlanningResult:
        """Extract the path from the tree."""
        path = []
        current = idx
        while current != -1:
            path.append(nodes[current])
            current = parents[current]
        path.reverse()

        actions = [PlanningAction(name="move", parameters={"position": p.tolist()}) for p in path]
        return PlanningResult(
            success=True,
            actions=actions,
            cost=cost,
            nodes_expanded=len(nodes),
            plan_length=len(path),
        )

    def set_collision_fn(self, fn: Callable) -> None:
        self._collision_fn = fn

    def get_stats(self) -> Dict[str, Any]:
        return {**super().get_stats(), "algorithm": "RRT*" if self.config.use_star else "RRT"}
