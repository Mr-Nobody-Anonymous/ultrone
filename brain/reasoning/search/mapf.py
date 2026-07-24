# Copyright (c) Ultrone Contributors. All rights reserved.
"""Multi-Agent Path Finding (MAPF) with Conflict-Based Search (CBS).

CBS is a two-level algorithm for finding collision-free paths for
multiple agents.  The high level searches a *constraint tree* (CT),
where each node represents a set of constraints prohibiting specific
agent–location–time occupancy.  The low level finds an optimal
individual path for each agent given those constraints.

Integration
-----------
Plugs into :class:`~brain.reasoning.tactical_engine.TacticalEngine`
as any other :class:`Planner` implementation.  Handles coordinated
movement of drone swarms, tank platoons, etc.
"""

from __future__ import annotations

import heapq
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple, Callable

from .base import Planner, PlanningAction, PlanningDomain, PlanningGoal, PlanningResult

logger = logging.getLogger("Ultrone.Brain.Reasoning.Search.MAPF")


@dataclass
class MAPFConfig:
    """Configuration for MAPF planners.

    Attributes
    ----------
    max_iterations:
        Maximum number of high-level CBS iterations.
    max_path_length:
        Maximum individual path length per agent.
    heuristics:
        One of ``"manhattan"``, ``"euclidean"``, or ``"zero"``.
    """
    max_iterations: int = 5000
    max_path_length: int = 100
    heuristics: str = "manhattan"


# ── CBS types ────────────────────────────────────────────────────────


@dataclass(frozen=True)
class Constraint:
    """A CBS constraint: agent *agent_id* cannot occupy *position* at *timestep*.

    If *timestep* is -1, the constraint is positional (any time).
    """
    agent_id: str
    position: Tuple[int, int]
    timestep: int = -1

    def __lt__(self, other: "Constraint") -> bool:
        return (self.agent_id, self.timestep) < (other.agent_id, other.timestep)


@dataclass
class _CTNode:
    """Constraint Tree node for CBS."""
    constraints: List[Constraint] = field(default_factory=list)
    paths: Dict[str, List[Tuple[int, int]]] = field(default_factory=dict)
    cost: float = 0.0
    depth: int = 0


# ═══════════════════════════════════════════════════════════════════════
#  MAPF Planner (wrapper around CBS)
# ═══════════════════════════════════════════════════════════════════════


class MAPFPlanner(Planner):
    """Multi-Agent Path Finding planner via Conflict-Based Search.

    Parameters
    ----------
    config:
        Hyper-parameters (see :class:`MAPFConfig`).
    """

    def __init__(self, config: Optional[MAPFConfig] = None) -> None:
        super().__init__()
        self.config = config or MAPFConfig()
        self._grid_width: int = 100
        self._grid_height: int = 100
        self._obstacles: Set[Tuple[int, int]] = set()
        self._agent_ids: List[str] = []
        self._starts: Dict[str, Tuple[int, int]] = {}
        self._goals: Dict[str, Tuple[int, int]] = {}

    # ── Lifecycle ────────────────────────────────────────────────────

    def initialize(self, domain: PlanningDomain) -> None:
        super().initialize(domain)

    def set_grid(
        self,
        width: int,
        height: int,
        obstacles: Optional[Set[Tuple[int, int]]] = None,
    ) -> None:
        """Configure the grid world."""
        self._grid_width = width
        self._grid_height = height
        self._obstacles = obstacles or set()

    def set_agents(
        self,
        agent_ids: List[str],
        starts: Dict[str, Tuple[int, int]],
        goals: Dict[str, Tuple[int, int]],
    ) -> None:
        """Set the agents and their start/goal positions."""
        self._agent_ids = list(agent_ids)
        self._starts = dict(starts)
        self._goals = dict(goals)

    # ── Core planning ────────────────────────────────────────────────

    def plan(self, state: Any, goal: PlanningGoal) -> PlanningResult:
        """Run CBS and return joint action sequence.

        The state is ignored (agent configurations are set separately
        via ``set_agents``).
        """
        result = self._cbs_search()

        if result.success:
            # Convert path dict to flat action sequence
            actions = self._paths_to_actions(result.paths)
            result.actions = actions
            result.plan_length = len(actions)

        logger.info(
            "MAPF plan: %s (agents=%d, cost=%.1f)",
            "FOUND" if result.success else "FAILED",
            len(self._agent_ids),
            result.cost,
        )
        return self._record_result(result)

    # ── CBS algorithm ────────────────────────────────────────────────

    def _cbs_search(self) -> PlanningResult:
        """High-level CBS search over the constraint tree."""
        # Root: no constraints, compute individual optimal paths
        root = _CTNode()
        for aid in self._agent_ids:
            path = self._astar_path(aid, [])
            if path is None:
                return PlanningResult(success=False, metadata={"reason": f"{aid} has no path"})
            root.paths[aid] = path
        root.cost = sum(len(p) for p in root.paths.values())

        # Priority queue on total cost
        open_set: List[Tuple[float, int, _CTNode]] = [(root.cost, 0, root)]
        _ctr = 1

        expanded = 0
        while open_set and expanded < self.config.max_iterations:
            expanded += 1
            _, _, node = heapq.heappop(open_set)

            # Detect first conflict
            conflict = self._find_first_conflict(node.paths)
            if conflict is None:
                # No conflict → solution found
                actions = self._paths_to_actions(node.paths)
                return PlanningResult(
                    success=True,
                    actions=actions,
                    cost=node.cost,
                    nodes_expanded=expanded,
                    plan_length=len(actions),
                    metadata={"depth": node.depth},
                )

            (aid_a, aid_b), pos, t = conflict

            # Resolve for agent A
            child_a = _CTNode(
                constraints=node.constraints + [Constraint(aid_a, pos, t)],
                depth=node.depth + 1,
            )
            for aid in self._agent_ids:
                path = self._astar_path(aid, child_a.constraints)
                if path is None:
                    child_a.paths[aid] = node.paths[aid]  # fallback
                else:
                    child_a.paths[aid] = path
            child_a.cost = sum(len(p) for p in child_a.paths.values())
            heapq.heappush(open_set, (child_a.cost, _ctr := _ctr + 1, child_a))

            # Resolve for agent B
            child_b = _CTNode(
                constraints=node.constraints + [Constraint(aid_b, pos, t)],
                depth=node.depth + 1,
            )
            for aid in self._agent_ids:
                path = self._astar_path(aid, child_b.constraints)
                if path is None:
                    child_b.paths[aid] = node.paths[aid]
                else:
                    child_b.paths[aid] = path
            child_b.cost = sum(len(p) for p in child_b.paths.values())
            heapq.heappush(open_set, (child_b.cost, _ctr := _ctr + 1, child_b))

        return PlanningResult(
            success=False,
            cost=float("inf"),
            nodes_expanded=expanded,
            metadata={"reason": "max_iterations_exceeded"},
        )

    def _find_first_conflict(
        self,
        paths: Dict[str, List[Tuple[int, int]]],
    ) -> Optional[Tuple[Tuple[str, str], Tuple[int, int], int]]:
        """Find the earliest vertex conflict among paths."""
        max_len = max(len(p) for p in paths.values())

        for t in range(max_len):
            occupied: Dict[Tuple[int, int], str] = {}
            for aid, path in paths.items():
                pos = path[t] if t < len(path) else path[-1]
                if pos in occupied:
                    return (occupied[pos], aid), pos, t
                occupied[pos] = aid
        return None

    def _astar_path(
        self,
        agent_id: str,
        constraints: List[Constraint],
    ) -> Optional[List[Tuple[int, int]]]:
        """Low-level A* for a single agent subject to constraints."""
        start = self._starts.get(agent_id)
        goal = self._goals.get(agent_id)
        if start is None or goal is None:
            return None

        # Build constraint lookup: (pos, time)
        pos_time_forbidden: Set[Tuple[Tuple[int, int], int]] = {
            (c.position, c.timestep) for c in constraints
        }

        open_set: List[Tuple[float, int, Tuple[int, int], int]] = []
        start_h = self._heuristic(start, goal)
        heapq.heappush(open_set, (start_h, 0, start, 0))

        came_from: Dict[Tuple[int, int, int], Tuple[int, int, int]] = {}
        g_score: Dict[Tuple[int, int, int], float] = {(start[0], start[1], 0): 0.0}

        while open_set:
            _, _, pos, t = heapq.heappop(open_set)
            key = (pos[0], pos[1], t)

            if pos == goal or t >= self.config.max_path_length:
                # Reconstruct
                path = self._reconstruct_path(start, came_from, pos, t)
                return path

            for dx, dy in [(0, 0), (1, 0), (-1, 0), (0, 1), (0, -1)]:
                nx, ny = pos[0] + dx, pos[1] + dy
                if nx < 0 or nx >= self._grid_width or ny < 0 or ny >= self._grid_height:
                    continue
                if (nx, ny) in self._obstacles:
                    continue
                if ((nx, ny), t + 1) in pos_time_forbidden:
                    continue

                next_key = (nx, ny, t + 1)
                tentative = g_score.get(key, float("inf")) + 1
                if tentative < g_score.get(next_key, float("inf")):
                    g_score[next_key] = tentative
                    f = tentative + self._heuristic((nx, ny), goal)
                    heapq.heappush(open_set, (f, t + 1, (nx, ny), t + 1))
                    came_from[next_key] = key

        return None

    # ── Helpers ──────────────────────────────────────────────────────

    def _heuristic(self, pos: Tuple[int, int], goal: Tuple[int, int]) -> float:
        if self.config.heuristics == "manhattan":
            return abs(pos[0] - goal[0]) + abs(pos[1] - goal[1])
        elif self.config.heuristics == "euclidean":
            return ((pos[0] - goal[0]) ** 2 + (pos[1] - goal[1]) ** 2) ** 0.5
        return 0.0

    def _reconstruct_path(
        self,
        start: Tuple[int, int],
        came_from: Dict[Tuple[int, int, int], Tuple[int, int, int]],
        pos: Tuple[int, int],
        t: int,
    ) -> List[Tuple[int, int]]:
        path: List[Tuple[int, int]] = []
        key = (pos[0], pos[1], t)
        while key in came_from:
            path.append((key[0], key[1]))
            key = came_from[key]
        path.append(start)
        path.reverse()
        return path

    def _paths_to_actions(
        self,
        paths: Dict[str, List[Tuple[int, int]]],
    ) -> List[PlanningAction]:
        """Convert per-agent path dict to a flat sequence."""
        actions: List[PlanningAction] = []
        max_len = max(len(p) for p in paths.values())
        for t in range(max_len):
            for aid, path in paths.items():
                pos = path[t] if t < len(path) else path[-1]
                actions.append(PlanningAction(
                    name="move",
                    parameters={"agent": aid, "position": pos},
                ))
        return actions

    def get_stats(self) -> Dict[str, Any]:
        stats = super().get_stats()
        stats["num_agents"] = len(self._agent_ids)
        return stats


# ═══════════════════════════════════════════════════════════════════════
#  ConflictBasedSearch alias
# ═══════════════════════════════════════════════════════════════════════

class ConflictBasedSearch(MAPFPlanner):
    """Alias for the CBS algorithm."""
    pass

