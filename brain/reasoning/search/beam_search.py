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

        for depth in range(self.config.max_depth):
            candidates: List[_BeamCandidate] = []

            for candidate in beam:
                # Goal check
                if candidate.state == target or (
                    self._terminal_fn and self._terminal_fn(candidate.state)
                ):
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
                    next_state = self._transition(state, action) if self._transition_fn else state
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

