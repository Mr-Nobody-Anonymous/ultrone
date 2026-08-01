# Copyright (c) Ultrone Contributors. All rights reserved.
"""Probabilistic Roadmap (PRM) planner for motion planning."""

from __future__ import annotations

import logging
import math
import random
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

from .base import Planner, PlanningAction, PlanningDomain, PlanningGoal, PlanningResult

logger = logging.getLogger("Ultrone.Brain.Reasoning.Search.PRM")


@dataclass
class PRMConfig:
    """Configuration for PRM."""
    num_samples: int = 100
    k_nearest: int = 5
    connection_distance: float = 50.0


class PRMPlanner(Planner):
    """Probabilistic Roadmap planner for continuous motion planning.

    Builds a graph of randomly sampled configurations and connects
    nearby nodes. Queries are solved by searching the graph.
    """

    def __init__(self, config: Optional[PRMConfig] = None) -> None:
        super().__init__()
        self.config = config or PRMConfig()
        self._nodes: List[Tuple[float, float]] = []
        self._edges: Dict[int, List[Tuple[int, float]]] = {}

    def initialize(self, domain: PlanningDomain) -> None:
        super().initialize(domain)

    def _build_roadmap(self, domain: PlanningDomain) -> None:
        """Build the probabilistic roadmap."""
        self._nodes = []
        self._edges = {}

        # Sample random nodes
        for _ in range(self.config.num_samples):
            if domain.state_shape and len(domain.state_shape) >= 2:
                x = random.uniform(0, domain.state_shape[0])
                y = random.uniform(0, domain.state_shape[1])
            else:
                x = random.uniform(0, 100)
                y = random.uniform(0, 100)
            self._nodes.append((x, y))

        # Connect nearest neighbours
        for i in range(len(self._nodes)):
            distances = [(j, math.sqrt((self._nodes[i][0] - self._nodes[j][0])**2 +
                                       (self._nodes[i][1] - self._nodes[j][1])**2))
                         for j in range(len(self._nodes)) if i != j]
            distances.sort(key=lambda x: x[1])
            self._edges[i] = []
            for j, d in distances[:self.config.k_nearest]:
                if d < self.config.connection_distance:
                    self._edges[i].append((j, d))

    def plan(self, state: Any, goal: PlanningGoal) -> PlanningResult:
        domain = self._domain
        if domain is None:
            raise RuntimeError("PRM not initialised — call .initialize() first.")

        self._build_roadmap(domain)

        # Find nearest node to start and goal
        if isinstance(state, tuple) and len(state) == 2:
            start_pos = (float(state[0]), float(state[1]))
        else:
            start_pos = (0.0, 0.0)

        target = goal.target_state
        if isinstance(target, tuple) and len(target) == 2:
            goal_pos = (float(target[0]), float(target[1]))
        else:
            goal_pos = (50.0, 50.0)

        # A* on roadmap
        start_idx = min(range(len(self._nodes)),
                       key=lambda i: math.sqrt((self._nodes[i][0] - start_pos[0])**2 +
                                                (self._nodes[i][1] - start_pos[1])**2))
        goal_idx = min(range(len(self._nodes)),
                      key=lambda i: math.sqrt((self._nodes[i][0] - goal_pos[0])**2 +
                                               (self._nodes[i][1] - goal_pos[1])**2))

        # Simple Dijkstra from start_idx to goal_idx
        open_set = {start_idx: 0.0}
        parent = {}
        closed = set()

        while open_set:
            current = min(open_set, key=open_set.get)
            cost = open_set.pop(current)
            if current in closed:
                continue
            closed.add(current)

            if current == goal_idx:
                # Reconstruct path
                path: List[PlanningAction] = []
                c = current
                while c in parent:
                    prev = parent[c]
                    path.append(PlanningAction("move", {"to": self._nodes[c]}))
                    c = prev
                path.reverse()
                result = PlanningResult(
                    success=True, actions=path, cost=cost, plan_length=len(path),
                )
                logger.info("PRM plan found: %d waypoints", len(path))
                return self._record_result(result)

            for neighbour, edge_cost in self._edges.get(current, []):
                if neighbour in closed:
                    continue
                new_cost = cost + edge_cost
                if new_cost < open_set.get(neighbour, float("inf")):
                    open_set[neighbour] = new_cost
                    parent[neighbour] = current

        result = PlanningResult(success=False, cost=float("inf"))
        logger.info("PRM plan FAILED")
        return self._record_result(result)
