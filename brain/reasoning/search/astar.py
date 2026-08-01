# Copyright (c) Ultrone Contributors. All rights reserved.
"""A*, D* Lite, and LPA* planners for grid-based pathfinding."""

from __future__ import annotations

import heapq
import logging
import math
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

from .base import Planner, PlanningAction, PlanningDomain, PlanningGoal, PlanningResult

logger = logging.getLogger("Ultrone.Brain.Reasoning.Search.AStar")


@dataclass
class AStarConfig:
    """Configuration for A* search."""
    heuristic_weight: float = 1.0
    max_expansions: int = 100_000
    allow_diagonal: bool = True


class AStar(Planner):
    """A* search planner for grid-based pathfinding."""

    def __init__(self, config: Optional[AStarConfig] = None) -> None:
        super().__init__()
        self.config = config or AStarConfig()
        self._heuristic_fn: Optional[Callable] = None

    def initialize(self, domain: PlanningDomain) -> None:
        super().initialize(domain)
        self._heuristic_fn = domain.heuristic_fn

    def _heuristic(self, state: Any, goal: Any) -> float:
        if self._heuristic_fn:
            return self._heuristic_fn(state, goal)
        if isinstance(state, tuple) and isinstance(goal, tuple):
            if len(state) == 2:
                return abs(state[0] - goal[0]) + abs(state[1] - goal[1])
        return 0.0

    def _get_neighbours(self, state: Any, target: Any, domain: PlanningDomain) -> List[Tuple[Any, float]]:
        """Get valid neighbours with costs."""
        if isinstance(state, tuple) and len(state) == 2:
            x, y = state
            neighbours = []
            moves = [(0, 1), (0, -1), (1, 0), (-1, 0)]
            if self.config.allow_diagonal:
                moves.extend([(1, 1), (1, -1), (-1, 1), (-1, -1)])
            for dx, dy in moves:
                nx, ny = x + dx, y + dy
                cost = 1.0 if abs(dx) + abs(dy) == 1 else math.sqrt(2)
                if domain.state_shape and len(domain.state_shape) == 2:
                    w, h = domain.state_shape
                    if 0 <= nx < w and 0 <= ny < h:
                        neighbours.append(((nx, ny), cost))
                else:
                    neighbours.append(((nx, ny), cost))
            return neighbours
        return [(state, 1.0)]

    def plan(self, state: Any, goal: PlanningGoal) -> PlanningResult:
        domain = self._domain
        if domain is None:
            raise RuntimeError("AStar not initialised — call .initialize() first.")

        start = state
        target = goal.target_state if goal.target_state is not None else state

        g_score: Dict[Any, float] = {start: 0.0}
        f_score: Dict[Any, float] = {start: self._heuristic(start, target)}
        open_set: List[Tuple[float, float, Any]] = [(f_score[start], id(start), start)]
        parent: Dict[Any, Any] = {}
        action_map: Dict[Tuple[Any, Any], PlanningAction] = {}
        closed: Set[Any] = set()
        expansions = 0

        while open_set and expansions < self.config.max_expansions:
            _, _, current = heapq.heappop(open_set)
            if current in closed:
                continue
            expansions += 1

            if current == target:
                # Reconstruct path
                path: List[PlanningAction] = []
                c = current
                while c in parent:
                    prev = parent[c]
                    path.append(action_map.get((prev, c), PlanningAction("move")))
                    c = prev
                path.reverse()
                result = PlanningResult(
                    success=True, actions=path, cost=g_score[current],
                    nodes_expanded=expansions, plan_length=len(path),
                )
                logger.info("A* plan found: len=%d, cost=%.2f", result.plan_length, result.cost)
                return self._record_result(result)

            closed.add(current)

            for neighbour, cost in self._get_neighbours(current, target, domain):
                if neighbour in closed:
                    continue
                tentative_g = g_score[current] + cost
                if tentative_g < g_score.get(neighbour, float("inf")):
                    parent[neighbour] = current
                    g_score[neighbour] = tentative_g
                    f = tentative_g + self._heuristic(neighbour, target) * self.config.heuristic_weight
                    heapq.heappush(open_set, (f, id(neighbour), neighbour))
                    action_map[(current, neighbour)] = PlanningAction("move", {"to": neighbour}, cost)

        result = PlanningResult(success=False, cost=float("inf"), nodes_expanded=expansions)
        logger.info("A* plan FAILED (expanded %d nodes)", expansions)
        return self._record_result(result)


class DLite(AStar):
    """D* Lite incremental replanning (stub)."""
    def __init__(self, config: Optional[AStarConfig] = None) -> None:
        super().__init__(config)
        self._astar = AStar(config)

    def initialize(self, domain: PlanningDomain) -> None:
        super().initialize(domain)
        self._astar.initialize(domain)

    def plan(self, state: Any, goal: PlanningGoal) -> PlanningResult:
        return self._astar.plan(state, goal)


class LPAStar(AStar):
    """LPA* (Lifelong Planning A*) incremental replanning (stub)."""
    def __init__(self, config: Optional[AStarConfig] = None) -> None:
        super().__init__(config)
        self._astar = AStar(config)

    def initialize(self, domain: PlanningDomain) -> None:
        super().initialize(domain)
        self._astar.initialize(domain)

    def plan(self, state: Any, goal: PlanningGoal) -> PlanningResult:
        return self._astar.plan(state, goal)
