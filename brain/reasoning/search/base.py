# Copyright (c) Ultrone Contributors. All rights reserved.
"""Abstract base class for all planning algorithms.

Every planner in this module implements ``Planner`` so they can be
swapped at runtime in the :class:`~brain.reasoning.tactical_engine.TacticalEngine`.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Generic, List, Optional, Tuple, TypeVar

logger = logging.getLogger("Ultrone.Brain.Reasoning.Search.Base")

# ── Core data types ──────────────────────────────────────────────────


@dataclass(frozen=True)
class PlanningAction:
    """A ground action that can be executed in the environment.

    Mirrors ``...reasoning.course_of_action.Action`` but is planner-agnostic
    so that search algorithms do not depend on the legacy action module.
    """
    name: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    cost: float = 1.0
    duration_ms: float = 0.0

    def __str__(self) -> str:
        return f"{self.name}({self.parameters})"


@dataclass
class PlanningDomain:
    """A description of the planning domain — state space, actions, costs.

    Fields
    ------
    state_shape:
        Descriptor of the state vector shape (for continuous planners).
    discrete_actions:
        List of all possible discrete actions.
    action_cost_fn:
        Optional callable(state, action) -> float cost.
    is_terminal_fn:
        Optional callable(state) -> bool indicating goal states.
    heuristic_fn:
        Optional callable(state) -> float estimate to goal.
    """
    state_shape: Optional[Tuple[int, ...]] = None
    discrete_actions: List[PlanningAction] = field(default_factory=list)
    action_cost_fn: Optional[Callable] = None
    is_terminal_fn: Optional[Callable] = None
    heuristic_fn: Optional[Callable] = None


@dataclass
class PlanningGoal:
    """Definition of what the planner should achieve."""
    description: str = ""
    predicates: Dict[str, Any] = field(default_factory=dict)
    target_state: Optional[Any] = None
    tolerance: float = 0.05
    is_terminal_fn: Optional[Callable] = None


@dataclass
class PlanningResult:
    """Result returned by a planner after a ``plan()`` call.

    Fields
    ------
    success:
        Whether a valid plan was found.
    actions:
        Sequence of actions forming the plan.
    cost:
        Total cumulative cost of the plan.
    nodes_expanded:
        Number of search nodes expanded (for benchmarking).
    plan_length:
        Number of actions in the plan.
    metadata:
        Planner-specific diagnostic information.
    """
    success: bool = False
    actions: List[PlanningAction] = field(default_factory=list)
    cost: float = float("inf")
    nodes_expanded: int = 0
    plan_length: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def is_valid(self) -> bool:
        """A plan is valid if it has at least one action and finite cost."""
        return self.success and len(self.actions) > 0 and self.cost < float("inf")


StateType = TypeVar("StateType")


class Planner(ABC, Generic[StateType]):
    """Abstract interface every planner must implement.

    Type parameter ``StateType`` is the representation used internally
    by the planner (e.g. ``np.ndarray``, ``tuple``, custom dataclass).
    """

    def __init__(self) -> None:
        self._domain: Optional[PlanningDomain] = None
        self._last_result: Optional[PlanningResult] = None
        self._total_plans: int = 0
        self._total_nodes: int = 0

    # ── Lifecycle ────────────────────────────────────────────────────

    @abstractmethod
    def initialize(self, domain: PlanningDomain) -> None:
        """Configure the planner with a description of the domain.

        Called once at system startup.  May be called again to reset.
        """
        self._domain = domain

    # ── Core ─────────────────────────────────────────────────────────

    @abstractmethod
    def plan(self, state: StateType, goal: PlanningGoal) -> PlanningResult:
        """Plan a sequence of actions from *state* that achieves *goal*.

        Returns
        -------
        PlanningResult
            Always returned (non-None); check ``result.success`` for validity.
        """
        ...

    def update(self, observation: Any) -> None:
        """Incorporate a new observation (relevant for online planners).

        Base implementation is a no-op; override in incremental planners.
        """
        pass

    # ── Diagnostics ──────────────────────────────────────────────────

    def get_stats(self) -> Dict[str, Any]:
        """Return diagnostic statistics about this planner."""
        return {
            "type": type(self).__name__,
            "total_plans": self._total_plans,
            "total_nodes_expanded": self._total_nodes,
            "avg_nodes_per_plan": (
                self._total_nodes / self._total_plans if self._total_plans else 0.0
            ),
        }

    def reset_stats(self) -> None:
        """Reset internal diagnostic counters."""
        self._total_plans = 0
        self._total_nodes = 0

    # ── Helpers for subclasses ───────────────────────────────────────

    def _record_result(self, result: PlanningResult) -> PlanningResult:
        """Increment counters and store the result."""
        self._total_plans += 1
        self._total_nodes += result.nodes_expanded
        self._last_result = result
        return result

    @property
    def last_result(self) -> Optional[PlanningResult]:
        return self._last_result
