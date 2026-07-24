# Copyright (c) Ultrone Contributors. All rights reserved.
"""Bidirectional Search planner.

Bidirectional search simultaneously expands from both the start state
and the goal state, meeting in the middle.  This can dramatically
reduce search time when the branching factor is large.

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

logger = logging.getLogger("Ultrone.Brain.Reasoning.Search.Bidirectional")


@dataclass
class BidirectionalConfig:
    """Configuration for Bidirectional Search.

    Attributes
    ----------
    max_expansions:
        Hard limit on total node expansions.
    heuristic_weight:
        Weight applied to heuristic.
    """
    max_expansions: int = 50_000
    heuristic_weight: float = 1.0


class BidirectionalSearch(Planner):
    """Bidirectional heuristic search.

    Maintains two frontiers (forward from start, backward from goal)
    and terminates when they intersect.
    """

    def __init__(self, config: Optional[BidirectionalConfig] = None) -> None:
        super().__init__()
        self.config = config or BidirectionalConfig()
        self._heuristic_fn: Optional[Callable] = None
        self._neighbour_fn: Optional[Callable] = None
        self._reverse_neighbour_fn: Optional[Callable] = None

    def initialize(self, domain: PlanningDomain) -> None:
        super().initialize(domain)
        self._heuristic_fn = domain.heuristic_fn
        # Default: symmetric neighbours
        self._neighbour_fn = domain.action_cost_fn
        self._reverse_neighbour_fn = None  # will be symmetric by default

    def plan(self, state: Any, goal: PlanningGoal) -> PlanningResult:
        domain = self._domain
        if domain is None:
            raise RuntimeError("BidirectionalSearch not initialised — call .initialize() first.")

        start = state
        target = goal.target_state if goal.target_state is not None else state

        # Frontiers as priority queues
        f_open = [(0.0, id(start), start)]
        b_open = [(0.0, id(target), target)]
        f_g: Dict[Any, float] = {start: 0.0}
        b_g: Dict[Any, float] = {target: 0.0}
        f_parent: Dict[Any, Any] = {}
        b_parent: Dict[Any, Any] = {}
        f_action: Dict[Tuple[Any, Any], PlanningAction] = {}
        b_action: Dict[Tuple[Any, Any], PlanningAction] = {}

        f_closed: Set[Any] = set()
        b_closed: Set[Any] = set()

        expansions = 0
        best_cost = float("inf")
        meeting_point = None

        while f_open and b_open and expansions < self.config.max_expansions:
            # Expand forward
            _, _, f_current = heapq.heappop(f_open)
            if f_current in f_closed:
                continue
            f_closed.add(f_current)
            expansions += 1

            # Check meeting
            if f_current in b_g:
                total = f_g[f_current] + b_g[f_current]
                if total < best_cost:
                    best_cost = total
                    meeting_point = f_current

            # Expand backward
            _, _, b_current = heapq.heappop(b_open)
            if b_current in b_closed:
                continue
            b_closed.add(b_current)
            expansions += 1

            if b_current in f_g:
                total = f_g[b_current] + b_g[b_current]
                if total < best_cost:
                    best_cost = total
                    meeting_point = b_current

            if meeting_point is not None and best_cost < float("inf"):
                break

            # Generate forward neighbours
            for nxt in self._get_neighbours(f_current, forward=True):
                cost = domain.action_cost_fn(f_current, nxt) if domain.action_cost_fn else 1.0
                new_g = f_g.get(f_current, 0.0) + cost
                if new_g < f_g.get(nxt, float("inf")):
                    f_g[nxt] = new_g
                    f = new_g + (self._heuristic_fn(nxt, target) if self._heuristic_fn else 0.0)
                    heapq.heappush(f_open, (f, id(nxt), nxt))
                    f_parent[nxt] = f_current
                    f_action[(f_current, nxt)] = PlanningAction("move", {"to": nxt}, cost)

            # Generate backward neighbours
            for nxt in self._get_neighbours(b_current, forward=False):
                cost = domain.action_cost_fn(b_current, nxt) if domain.action_cost_fn else 1.0
                new_g = b_g.get(b_current, 0.0) + cost
                if new_g < b_g.get(nxt, float("inf")):
                    b_g[nxt] = new_g
                    b = new_g + (self._heuristic_fn(start, nxt) if self._heuristic_fn else 0.0)
                    heapq.heappush(b_open, (b, id(nxt), nxt))
                    b_parent[nxt] = b_current
                    b_action[(b_current, nxt)] = PlanningAction("move", {"to": nxt}, cost)

        # Reconstruct full path
        if meeting_point is not None:
            # Forward path
            forward_path: List[PlanningAction] = []
            cur = meeting_point
            while cur in f_parent:
                prev = f_parent[cur]
                forward_path.append(f_action.get((prev, cur), PlanningAction("move")))
                cur = prev
            forward_path.reverse()

            # Backward path
            backward_path: List[PlanningAction] = []
            cur = meeting_point
            while cur in b_parent:
                next_node = b_parent[cur]
                backward_path.append(b_action.get((cur, next_node), PlanningAction("move")))
                cur = next_node

            full_path = forward_path + backward_path
            result = PlanningResult(
                success=True,
                actions=full_path,
                cost=best_cost,
                nodes_expanded=expansions,
                plan_length=len(full_path),
                metadata={"meeting_point": str(meeting_point)},
            )
            logger.info("Bidirectional plan found: len=%d, cost=%.2f", result.plan_length, result.cost)
            return self._record_result(result)

        result = PlanningResult(
            success=False, cost=float("inf"), nodes_expanded=expansions
        )
        logger.info("Bidirectional plan FAILED (expanded %d nodes)", expansions)
        return self._record_result(result)

    def _get_neighbours(self, state: Any, forward: bool = True) -> List[Any]:
        """Return neighbour states. Override for domain-specific dynamics."""
        if forward and self._neighbour_fn:
            return self._neighbour_fn(state)
        if not forward and self._reverse_neighbour_fn:
            return self._reverse_neighbour_fn(state)
        return [state]  # identity fallback

