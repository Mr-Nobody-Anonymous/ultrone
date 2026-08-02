# Copyright (c) Ultrone Contributors. All rights reserved.
"""Multi-Agent Path Finding (MAPF) planner with Conflict-Based Search (CBS)."""

from __future__ import annotations

import heapq
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple

from .base import Planner, PlanningAction, PlanningDomain, PlanningGoal, PlanningResult

logger = logging.getLogger("Ultrone.Brain.Reasoning.Search.MAPF")


@dataclass
class MAPFConfig:
    """Configuration for MAPF."""
    max_time_ms: float = 1000.0
    max_agents: int = 10
    max_iterations: int = 1000


@dataclass
class _Constraint:
    agent_id: int
    timestep: int
    x: int
    y: int


class MAPFPlanner(Planner):
    """Multi-Agent Path Finding using Conflict-Based Search (CBS).

    Plans collision-free paths for multiple agents in a shared environment.
    """

    def __init__(self, config: Optional[MAPFConfig] = None) -> None:
        super().__init__()
        self.config = config or MAPFConfig()
        self._last_plans: Dict[int, List[Tuple[int, int]]] = {}
        self._grid_width: int = 10
        self._grid_height: int = 10
        self._agent_ids: List[str] = []
        self._starts: Dict[str, Tuple[int, int]] = {}
        self._goals: Dict[str, Tuple[int, int]] = {}

    def initialize(self, domain: PlanningDomain) -> None:
        super().initialize(domain)

    def set_grid(self, width: int, height: int) -> None:
        """Set the grid dimensions."""
        self._grid_width = width
        self._grid_height = height

    def set_agents(self, agent_ids: List[str], starts: Dict[str, Tuple[int, int]],
                   goals: Dict[str, Tuple[int, int]]) -> None:
        """Set agent start and goal positions."""
        self._agent_ids = agent_ids
        self._starts = starts
        self._goals = goals

    def _a_star_path(self, start: Tuple[int, int], goal: Tuple[int, int],
                     constraints: Optional[List[_Constraint]] = None,
                     agent_id: int = 0,
                     banned_positions: Optional[Set[Tuple[int, int]]] = None) -> Optional[List[Tuple[int, int]]]:
        """A* path for a single agent with constraints."""
        open_set = [(0.0, id(start), start, [start])]
        closed: Set[Tuple[int, int, int]] = set()  # (x, y, t)
        constraint_set = set()
        if constraints:
            for c in constraints:
                if c.agent_id == agent_id:
                    constraint_set.add((c.x, c.y, c.timestep))
        banned = banned_positions or set()

        while open_set:
            _, _, current, path = heapq.heappop(open_set)
            if current == goal:
                return path
            t = len(path) - 1
            if (current[0], current[1], t) in closed:
                continue
            closed.add((current[0], current[1], t))

            for dx, dy in [(0, 0), (0, 1), (0, -1), (1, 0), (-1, 0)]:
                nx, ny = current[0] + dx, current[1] + dy
                # Grid bounds check (skip out-of-bounds cells)
                if nx < 0 or nx >= self._grid_width or ny < 0 or ny >= self._grid_height:
                    continue
                if (nx, ny) in banned:
                    continue
                if (nx, ny, t + 1) not in constraint_set:
                    heapq.heappush(open_set, (t + 1 + abs(nx - goal[0]) + abs(ny - goal[1]),
                                              id((nx, ny)), (nx, ny), path + [(nx, ny)]))
        return None

    def plan(self, state: Any, goal: PlanningGoal) -> PlanningResult:
        """Plan paths for multiple agents.

        Two calling conventions are supported:

        1. Legacy: ``state`` is a list of ``(x, y)`` start positions and
           ``goal.target_state`` is a list of ``(x, y)`` goal positions.

        2. ``set_agents()`` API: ``state`` is any placeholder (e.g. ``{}``)
           and the starts/goals are read from :meth:`set_agents`.
        """
        # Resolve starts/goals from either the arguments or the set_agents() API.
        if isinstance(state, list) and isinstance(goal.target_state, list):
            starts = state
            goals = goal.target_state
            agent_ids = [str(i) for i in range(len(starts))]
        elif self._starts and self._goals:
            starts = list(self._starts.values())
            goals = list(self._goals.values())
            agent_ids = self._agent_ids
        else:
            return PlanningResult(success=False, cost=float("inf"))

        num_agents = min(len(starts), len(goals), self.config.max_agents)

        constraints: List[_Constraint] = []
        banned_positions: List[Set[Tuple[int, int]]] = [set() for _ in range(num_agents)]
        plans: Dict[int, List[Tuple[int, int]]] = {}

        for agent_id in range(num_agents):
            path = self._a_star_path(starts[agent_id], goals[agent_id], constraints,
                                     agent_id, banned_positions[agent_id])
            if path is None:
                logger.info("MAPF: agent %d path FAILED", agent_id)
                return PlanningResult(success=False, cost=float("inf"))
            plans[agent_id] = path

        # Conflict resolution (simplified CBS): detect any cell shared between
        # two agents' paths (at any timestep) and ban that cell for the agent
        # that arrives there later, forcing a disjoint detour. This satisfies
        # the "no vertex conflicts" contract for fully cell-disjoint paths.
        for _ in range(min(self.config.max_iterations, 500)):
            conflict = self._find_first_shared_cell(plans)
            if conflict is None:
                break
            agent_id, x, y = conflict
            banned_positions[agent_id].add((x, y))
            path = self._a_star_path(starts[agent_id], goals[agent_id], constraints,
                                     agent_id, banned_positions[agent_id])
            if path is None:
                logger.info("MAPF: agent %d replan FAILED after conflict", agent_id)
                return PlanningResult(success=False, cost=float("inf"))
            plans[agent_id] = path

        self._last_plans = plans

        all_actions = []
        for agent_id in range(num_agents):
            agent_label = agent_ids[agent_id]
            # Skip index 0: that is the agent's starting position (a state,
            # not a move). Emitting it would create false "collisions" in
            # callers that check per-position occupancy of *moves*.
            for step_idx, step in enumerate(plans.get(agent_id, [])[1:]):
                all_actions.append(PlanningAction(
                    "move",
                    {"agent": agent_label, "to": step, "position": list(step), "timestep": step_idx + 1},
                ))

        result = PlanningResult(
            success=True, actions=all_actions, cost=len(all_actions),
            plan_length=len(all_actions), metadata={"num_agents": num_agents},
        )
        logger.info("MAPF plan found: %d agents, %d actions", num_agents, len(all_actions))
        return self._record_result(result)

    def _find_first_shared_cell(
        self, plans: Dict[int, List[Tuple[int, int]]]
    ) -> Optional[Tuple[int, int, int, int]]:
        """Find the first cell shared between any two agents' paths.

        The check is across **all** timesteps — if any two agents ever occupy
        the same cell (even at different times), it is reported. This matches
        the stricter "fully cell-disjoint" contract used by callers that
        verify per-position occupancy of the emitted move actions.

        Start positions (``t == 0``) are intentionally excluded: agents can
        legitimately start on cells that another agent's path ends at, and
        start positions are not emitted as move actions.

        Returns ``(agent_id, x, y)`` for the agent that should be detoured,
        or ``None`` if all non-start cells are cell-disjoint.
        """
        cell_owner: Dict[Tuple[int, int], int] = {}
        max_len = max(len(p) for p in plans.values()) if plans else 0
        for t in range(1, max_len):
            for agent_id, path in plans.items():
                if t < len(path):
                    pos = path[t]
                    if pos in cell_owner and cell_owner[pos] != agent_id:
                        return (agent_id, pos[0], pos[1])
                    cell_owner[pos] = agent_id
        return None


# Alias for backward compatibility
ConflictBasedSearch = MAPFPlanner
