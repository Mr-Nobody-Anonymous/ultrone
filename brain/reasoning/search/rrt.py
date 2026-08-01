# Copyright (c) Ultrone Contributors. All rights reserved.
"""Rapidly-exploring Random Tree (RRT) planner for motion planning."""

from __future__ import annotations

import logging
import math
import random
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

from .base import Planner, PlanningAction, PlanningDomain, PlanningGoal, PlanningResult

logger = logging.getLogger("Ultrone.Brain.Reasoning.Search.RRT")


@dataclass
class RRTConfig:
    """Configuration for RRT."""
    max_iterations: int = 1000
    step_size: float = 5.0
    goal_sample_rate: float = 0.1
    goal_tolerance: float = 5.0


class RRTPlanner(Planner):
    """Rapidly-exploring Random Tree planner for motion planning.

    Builds a tree by randomly sampling points and extending towards
    them from the nearest node. Efficient for high-dimensional spaces.
    """

    def __init__(self, config: Optional[RRTConfig] = None) -> None:
        super().__init__()
        self.config = config or RRTConfig()

    def initialize(self, domain: PlanningDomain) -> None:
        super().initialize(domain)

    def _steer(self, from_node: Tuple[float, float], to_node: Tuple[float, float]) -> Tuple[float, float]:
        """Steer from from_node towards to_node by step_size."""
        dx = to_node[0] - from_node[0]
        dy = to_node[1] - from_node[1]
        dist = math.sqrt(dx**2 + dy**2)
        if dist < self.config.step_size:
            return to_node
        ratio = self.config.step_size / dist
        return (from_node[0] + dx * ratio, from_node[1] + dy * ratio)

    def _sample(self) -> Tuple[float, float]:
        """Sample a random point in the state space."""
        return (random.uniform(0, 100), random.uniform(0, 100))

    def plan(self, state: Any, goal: PlanningGoal) -> PlanningResult:
        start = (float(state[0]), float(state[1])) if isinstance(state, tuple) and len(state) == 2 else (0.0, 0.0)
        target = goal.target_state
        if isinstance(target, tuple) and len(target) == 2:
            goal_pos = (float(target[0]), float(target[1]))
        else:
            goal_pos = (50.0, 50.0)

        nodes = [start]
        parent: Dict[int, int] = {}
        goal_idx = -1

        for i in range(self.config.max_iterations):
            # Sample (with goal bias)
            if random.random() < self.config.goal_sample_rate:
                sample = goal_pos
            else:
                sample = self._sample()

            # Find nearest node
            nearest_idx = min(range(len(nodes)),
                             key=lambda i: math.sqrt((nodes[i][0] - sample[0])**2 +
                                                      (nodes[i][1] - sample[1])**2))

            # Steer
            new_node = self._steer(nodes[nearest_idx], sample)
            nodes.append(new_node)
            parent[len(nodes) - 1] = nearest_idx

            # Check if reached goal
            if math.sqrt((new_node[0] - goal_pos[0])**2 + (new_node[1] - goal_pos[1])**2) < self.config.goal_tolerance:
                goal_idx = len(nodes) - 1
                break

        if goal_idx < 0:
            return PlanningResult(success=False, cost=float("inf"))

        # Reconstruct path
        path: List[PlanningAction] = []
        idx = goal_idx
        while idx in parent:
            path.append(PlanningAction("move", {"to": nodes[idx]}))
            idx = parent[idx]
        path.reverse()

        result = PlanningResult(
            success=True, actions=path, cost=len(path), plan_length=len(path),
        )
        logger.info("RRT plan found: %d waypoints (%d iterations)", len(path), self.config.max_iterations)
        return self._record_result(result)
