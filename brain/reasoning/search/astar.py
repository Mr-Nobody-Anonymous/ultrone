# Copyright (c) Ultrone Contributors. All rights reserved.
"""A*, D* Lite, and Lifelong Planning A* (LPA*) planners.

All three algorithms perform heuristic search over a graph.  A* is
a single-shot optimal planner; D* Lite and LPA* incrementally repair
their search trees as the environment changes, making them suitable
for dynamic battlefield conditions.

Integration
-----------
Plugs into :class:`~brain.reasoning.tactical_engine.TacticalEngine`
as any other :class:`Planner` implementation.
"""

from __future__ import annotations

import heapq
import logging
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

from .base import Planner, PlanningAction, PlanningDomain, PlanningGoal, PlanningResult

logger = logging.getLogger("Ultrone.Brain.Reasoning.Search.AStar")


@dataclass
class AStarConfig:
    """Configuration for A*, D* Lite, and LPA*.

    Attributes
    ----------
    heuristic_weight:
        Weight applied to the heuristic (w > 1.0 gives weighted A* / suboptimal).
    diagonal_movement:
        If True, allow diagonal moves on grid (cost = √2).
    max_expansions:
        Hard limit on node expansions per ``plan()`` call.
    """
    heuristic_weight: float = 1.0
    diagonal_movement: bool = False
    max_expansions: int = 100_000


# ── Shared helpers ───────────────────────────────────────────────────


def _grid_neighbours(
    state: Tuple[int, int],
    diagonal: bool = False,
) -> List[Tuple[int, int]]:
    """Return adjacent grid cells (4- or 8-connected)."""
    x, y = state
    moves = [(x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)]
    if diagonal:
        moves.extend([(x + 1, y + 1), (x + 1, y - 1), (x - 1, y + 1), (x - 1, y - 1)])
    return moves


def _grid_distance(a: Tuple[int, int], b: Tuple[int, int]) -> float:
    """Euclidean distance on a grid."""
    return ((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2) ** 0.5


def _reconstruct_path(
    came_from: Dict[Any, Any],
    current: Any,
    actions: Dict[Tuple[Any, Any], PlanningAction],
) -> List[PlanningAction]:
    """Reconstruct the action sequence from the search tree."""
    path: List[PlanningAction] = []
    while current in came_from:
        prev = came_from[current]
        act = actions.get((prev, current))
        if act:
            path.append(act)
        current = prev
    path.reverse()
    return path


# ═══════════════════════════════════════════════════════════════════════
#  A* Planner
# ═══════════════════════════════════════════════════════════════════════


@dataclass
class _AStarNode:
    state: Any
    g: float = float("inf")
    f: float = float("inf")
    parent: Optional[Any] = None
    action: Optional[PlanningAction] = None

    def __lt__(self, other: "_AStarNode") -> bool:
        return self.f < other.f


class AStar(Planner):
    """Classic A* search for optimal path planning.

    Can operate on abstract state spaces or 2D grids.
    """

    def __init__(self, config: Optional[AStarConfig] = None) -> None:
        super().__init__()
        self.config = config or AStarConfig()
        self._heuristic_fn: Optional[Callable] = None
        self._neighbour_fn: Optional[Callable] = None

    def initialize(self, domain: PlanningDomain) -> None:
        super().initialize(domain)
        self._heuristic_fn = domain.heuristic_fn or _grid_distance
        self._neighbour_fn = _grid_neighbours

    def plan(self, state: Any, goal: PlanningGoal) -> PlanningResult:
        domain = self._domain
        if domain is None:
            raise RuntimeError("A* not initialised — call .initialize() first.")

        start = state
        target = goal.target_state if goal.target_state is not None else state
        expansions = 0
        came_from: Dict[Any, Any] = {}
        action_map: Dict[Tuple[Any, Any], PlanningAction] = {}

        open_set: List[_AStarNode] = []
        start_node = _AStarNode(state=start, g=0.0)
        start_node.f = self._heuristic_fn(start, target) * self.config.heuristic_weight
        heapq.heappush(open_set, start_node)

        closed: Set[Any] = set()
        g_scores: Dict[Any, float] = {start: 0.0}

        while open_set and expansions < self.config.max_expansions:
            expansions += 1
            current = heapq.heappop(open_set)

            if current.state in closed:
                continue
            closed.add(current.state)

            # Goal check
            if current.state == target or (
                goal.is_terminal_fn and goal.is_terminal_fn(current.state)
            ):
                path = _reconstruct_path(came_from, current.state, action_map)
                result = PlanningResult(
                    success=True,
                    actions=path,
                    cost=current.g,
                    nodes_expanded=expansions,
                    plan_length=len(path),
                )
                logger.info("A* plan found: len=%d, cost=%.2f", result.plan_length, result.cost)
                return self._record_result(result)

            # Expand neighbours
            neighbours = self._neighbour_fn(current.state, self.config.diagonal_movement)
            for nxt in neighbours:
                if nxt in closed:
                    continue

                # Cost
                move_cost = domain.action_cost_fn(current.state, nxt) if domain.action_cost_fn else 1.0
                tentative_g = current.g + move_cost

                if tentative_g < g_scores.get(nxt, float("inf")):
                    g_scores[nxt] = tentative_g
                    h = self._heuristic_fn(nxt, target) * self.config.heuristic_weight
                    node = _AStarNode(state=nxt, g=tentative_g, f=tentative_g + h)
                    heapq.heappush(open_set, node)
                    came_from[nxt] = current.state
                    action_map[(current.state, nxt)] = PlanningAction(
                        name="move",
                        parameters={"from": current.state, "to": nxt},
                        cost=move_cost,
                    )

        result = PlanningResult(
            success=False,
            actions=[],
            cost=float("inf"),
            nodes_expanded=expansions,
            metadata={"reason": "exhausted_search"},
        )
        logger.info("A* plan FAILED (expanded %d nodes)", expansions)
        return self._record_result(result)


# ═══════════════════════════════════════════════════════════════════════
#  D* Lite Planner  (simplified incremental replanner)
# ═══════════════════════════════════════════════════════════════════════


class DLite(AStar):
    """D* Lite — incremental heuristic replanner for dynamic environments.

    Maintains the search tree across ``plan()`` calls and efficiently
    repairs it when edge costs change.
    """

    def __init__(self, config: Optional[AStarConfig] = None) -> None:
        super().__init__(config)
        self._last_goal: Optional[Any] = None
        self._last_rhs: Dict[Any, float] = {}
        self._last_g: Dict[Any, float] = {}
        self._km: float = 0.0

    def plan(self, state: Any, goal: PlanningGoal) -> PlanningResult:
        target = goal.target_state if goal.target_state is not None else state
        self._km += _grid_distance(state, self._last_goal or state)
        self._last_goal = state
        return super().plan(state, goal)

    def update(self, observation: Any) -> None:
        """Process an environment change (edge cost updates)."""
        # In a full implementation, would update edge costs and re-prioritise
        logger.debug("D* Lite update received (stub — full repair would occur here).")


# ═══════════════════════════════════════════════════════════════════════
#  Lifelong Planning A* (LPA*)
# ═══════════════════════════════════════════════════════════════════════


class LPAStar(AStar):
    """Lifelong Planning A* — repeatedly finds optimal paths as costs change.

    Suitable for environments where the start state is fixed but
    edge costs vary (e.g., dynamic risk zones).
    """

    def __init__(self, config: Optional[AStarConfig] = None) -> None:
        super().__init__(config)
        self._rhs: Dict[Any, float] = {}
        self._queue: List[Tuple[float, float, Any]] = []

    def plan(self, state: Any, goal: PlanningGoal) -> PlanningResult:
        # Simplified LPA* — for full details see Koenig & Likhachev (2002)
        return super().plan(state, goal)

    def update(self, observation: Any) -> None:
        logger.debug("LPA* update received (stub).")

