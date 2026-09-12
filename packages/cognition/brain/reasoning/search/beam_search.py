# Copyright (c) Ultrone Contributors. All rights reserved.
"""Beam Search planner.

Beam Search is a width-limited heuristic search that maintains the
top-*k* most promising candidates at each depth level.  It trades
optimality for significantly lower memory and computation,
making it suitable for real-time tactical planning with large
branching factors.

Integration
-----------
Plugs into :class:`~brain.reasoning.tactical_engine.TacticalEngine`
as any other :class:`Planner` implementation.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple

from .base import Planner, PlanningAction, PlanningDomain, PlanningGoal, PlanningResult

logger = logging.getLogger("Ultrone.Brain.Reasoning.Search.Beam")


@dataclass
class BeamSearchConfig:
    """Configuration for Beam Search.

    Attributes
    ----------
    beam_width:
        Number of candidate sequences retained at each depth (k).
    max_depth:
        Maximum plan length.
    heuristic_weight:
        Weight applied to the heuristic score.
    """
    beam_width: int = 10
    max_depth: int = 50
    heuristic_weight: float = 1.0


@dataclass
class _BeamCandidate:
    actions: List[PlanningAction] = field(default_factory=list)
    state: Any = None
    cost: float = 0.0
    score: float = 0.0  # heuristic + cost


class BeamSearch(Planner):
    """Beam Search planner.

    Parameters
    ----------
    config:
        Hyper-parameters (see :class:`BeamSearchConfig`).
    """

    def __init__(self, config: Optional[BeamSearchConfig] = None) -> None:
        super().__init__()
        self.config = config or BeamSearchConfig()
        self._heuristic_fn: Optional[Callable] = None
        self._transition_fn: Optional[Callable] = None
        self._terminal_fn: Optional[Callable] = None

    def initialize(self, domain: PlanningDomain) -> None:
        super().initialize(domain)
        self._heuristic_fn = domain.heuristic_fn
        self._transition_fn = domain.action_cost_fn
        self._terminal_fn = domain.is_terminal_fn

    def _transition(self, state: Any, action: PlanningAction) -> Optional[Any]:
        """Apply an action to a state and return the next state.

        For grid-based domains, uses action parameters to compute next state.
        Returns ``None`` if the resulting state is out of bounds.
        """
        if isinstance(state, tuple) and len(state) == 2:
            x, y = state
            params = action.parameters
            dx = params.get("dx", 0)
            dy = params.get("dy", 0)
            nx, ny = x + dx, y + dy
            # Bounds check against the domain's state_shape if available
            if self._domain is not None and hasattr(self._domain, 'state_shape'):
                shape = self._domain.state_shape
                if isinstance(shape, tuple) and len(shape) == 2:
                    if nx < 0 or nx >= shape[0] or ny < 0 or ny >= shape[1]:
                        return None
            return (nx, ny)
        return state

    def plan(self, state: Any, goal: PlanningGoal) -> PlanningResult:
        domain = self._domain
        if domain is None:
            raise RuntimeError("BeamSearch not initialised — call .initialize() first.")

        target = goal.target_state if goal.target_state is not None else state
        h_fn = self._heuristic_fn or (lambda s, g: 0.0)

        # Initialise beam with the start state
        beam: List[_BeamCandidate] = [
            _BeamCandidate(actions=[], state=state, cost=0.0, score=h_fn(state, target))
        ]

        nodes_expanded = 0

        goal_check = goal.is_terminal_fn or self._terminal_fn

        for depth in range(self.config.max_depth):
            candidates: List[_BeamCandidate] = []

            for candidate in beam:
                # Goal check
                is_goal = (candidate.state == target)
                if not is_goal and goal_check:
                    is_goal = goal_check(candidate.state)
                if is_goal:
                    result = PlanningResult(
                        success=True,
                        actions=candidate.actions,
                        cost=candidate.cost,
                        nodes_expanded=nodes_expanded,
                        plan_length=len(candidate.actions),
                    )
                    logger.info("Beam plan found: len=%d, cost=%.2f", result.plan_length, result.cost)
                    return self._record_result(result)

                # Expand
                for action in domain.discrete_actions:
                    nodes_expanded += 1
                    next_state = self._transition(candidate.state, action)
                    if next_state is None:
                        continue
                    new_cost = candidate.cost + action.cost
                    new_score = new_cost + h_fn(next_state, target) * self.config.heuristic_weight

                    candidates.append(
                        _BeamCandidate(
                            actions=candidate.actions + [action],
                            state=next_state,
                            cost=new_cost,
                            score=new_score,
                        )
                    )

            # Prune to beam width
            if not candidates:
                break
            candidates.sort(key=lambda c: c.score)
            beam = candidates[: self.config.beam_width]

        result = PlanningResult(
            success=False,
            actions=[],
            cost=float("inf"),
            nodes_expanded=nodes_expanded,
            metadata={"reason": "depth_limit"},
        )
        logger.info("Beam plan FAILED (expanded %d nodes)", nodes_expanded)
        return self._record_result(result)
