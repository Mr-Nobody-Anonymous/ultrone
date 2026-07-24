# Copyright (c) Ultrone Contributors. All rights reserved.
"""Hierarchical Task Network (HTN) planner.

HTN planning decomposes high-level compound tasks into primitive
actions via a library of *methods*.  Each method describes one way
to accomplish a compound task as a sequence of sub-tasks (which may
themselves be compound).  The planner searches the decomposition
space for a sequence of primitive actions that achieves the goal.

Integration
-----------
Plugs into :class:`~brain.reasoning.tactical_engine.TacticalEngine`
as any other :class:`Planner` implementation.  Useful for structured
military doctrine where high-level missions decompose into standard
operating procedures.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple, Set

from .base import Planner, PlanningAction, PlanningDomain, PlanningGoal, PlanningResult

logger = logging.getLogger("Ultrone.Brain.Reasoning.Search.HTN")


# ── HTN-specific types ───────────────────────────────────────────────


@dataclass(frozen=True)
class Task:
    """A task that the planner must accomplish.

    Parameters
    ----------
    name:
        Unique task identifier.
    parameters:
        Task-specific parameters.
    is_primitive:
        If True, the task maps directly to a :class:`PlanningAction`.
    """
    name: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    is_primitive: bool = False

    def __str__(self) -> str:
        return f"{'!' if self.is_primitive else '?'}{self.name}"


@dataclass
class PrimitiveTask(Task):
    """A task that maps directly to a planning action."""
    action: Optional[PlanningAction] = None

    def __init__(
        self,
        name: str,
        action: Optional[PlanningAction] = None,
        parameters: Optional[Dict[str, Any]] = None,
    ) -> None:
        super().__init__(name=name, parameters=parameters or {}, is_primitive=True)
        self.action = action or PlanningAction(name=name, parameters=parameters or {})


@dataclass
class CompoundTask(Task):
    """A task that must be decomposed via a method."""
    def __init__(self, name: str, parameters: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(name=name, parameters=parameters or {}, is_primitive=False)


@dataclass
class Method:
    """A way to decompose a compound task into sub-tasks.

    Attributes
    ----------
    task_name:
        The compound task this method applies to.
    subtasks:
        Ordered list of sub-tasks (compound or primitive).
    preconditions:
        Optional callable(state) -> bool; if False the method is inapplicable.
    cost:
        Additional cost of applying this method.
    description:
        Human-readable explanation of this decomposition.
    """
    task_name: str
    subtasks: List[Task] = field(default_factory=list)
    preconditions: Optional[Callable[[Any], bool]] = None
    cost: float = 1.0
    description: str = ""


@dataclass
class HTNConfig:
    """Configuration for the HTN planner.

    Attributes
    ----------
    max_depth:
        Maximum decomposition depth (guard against infinite recursion).
    breadth_first:
        If True, search decomposition space breadth-first; otherwise depth-first.
    """
    max_depth: int = 20
    breadth_first: bool = False


# ── HTN Planner ──────────────────────────────────────────────────────


class HTNPlanner(Planner):
    """Hierarchical Task Network planner.

    Operates on a library of :class:`Task` definitions and
    :class:`Method` decompositions.  The planner decomposes compound
    tasks until a sequence of primitive actions is obtained.

    Example
    -------
    >>> planner = HTNPlanner()
    >>> planner.add_method(Method(task_name="neutralise_target",
    ...                           subtasks=[Task("locate"), Task("engage"), Task("assess")]))
    >>> planner.add_primitive(PrimitiveTask("locate", action=PlanningAction("scan")))
    >>> result = planner.plan(initial_state, goal)
    """

    def __init__(self, config: Optional[HTNConfig] = None) -> None:
        super().__init__()
        self.config = config or HTNConfig()
        self._methods: Dict[str, List[Method]] = {}
        self._primitives: Dict[str, PrimitiveTask] = {}

    # ── HTN library construction ─────────────────────────────────────

    def add_method(self, method: Method) -> None:
        """Register a decomposition method for a compound task."""
        self._methods.setdefault(method.task_name, []).append(method)

    def add_primitive(self, task: PrimitiveTask) -> None:
        """Register a primitive task that maps to an action."""
        self._primitives[task.name] = task

    def add_tasks(self, tasks: Sequence[Task]) -> None:
        """Bulk-add tasks; compound tasks require subsequent ``add_method`` calls."""
        for t in tasks:
            if t.is_primitive:
                if isinstance(t, PrimitiveTask):
                    self.add_primitive(t)
            else:
                pass  # methods added separately

    # ── Lifecycle ────────────────────────────────────────────────────

    def initialize(self, domain: PlanningDomain) -> None:
        super().initialize(domain)
        # Auto-register primitive actions from domain
        for action in domain.discrete_actions:
            self.add_primitive(PrimitiveTask(action.name, action))

    # ── Core planning ────────────────────────────────────────────────

    def plan(self, state: Any, goal: PlanningGoal) -> PlanningResult:
        """Decompose the goal into a sequence of primitive actions.

        The planner uses depth-first search with cycle prevention.
        """
        # Convert goal into a top-level compound task
        top_task = CompoundTask(
            name=goal.description if goal.description else "achieve_goal",
            parameters=goal.predicates,
        )
        if top_task.name not in self._methods and top_task.name not in self._primitives:
            # Auto-map goal name to method if possible
            logger.warning("No method or primitive for top task '%s' — registering empty.", top_task.name)
            self.add_method(Method(task_name=top_task.name, subtasks=[]))

        # Decompose
        plan: List[PlanningAction] = []
        visited: Set[str] = set()
        success = self._decompose(top_task, state, plan, visited, depth=0)

        result = PlanningResult(
            success=success,
            actions=plan,
            cost=sum(a.cost for a in plan),
            plan_length=len(plan),
            metadata={"top_task": top_task.name},
        )
        logger.info(
            "HTN plan: %s (len=%d, cost=%.2f)",
            "FOUND" if success else "FAILED",
            result.plan_length,
            result.cost,
        )
        return self._record_result(result)

    def _decompose(
        self,
        task: Task,
        state: Any,
        plan: List[PlanningAction],
        visited: Set[str],
        depth: int,
    ) -> bool:
        """Recursive task decomposition.

        Returns True if the task was successfully decomposed into actions.
        """
        if depth > self.config.max_depth:
            logger.debug("HTN max depth reached for %s", task)
            return False

        # Cycle prevention
        if task.name in visited:
            logger.debug("HTN cycle detected on %s", task)
            return False

        # Primitive task → emit action
        if task.is_primitive:
            primitive = self._primitives.get(task.name)
            if primitive and primitive.action:
                plan.append(primitive.action)
                return True
            logger.warning("No primitive registered for '%s'", task.name)
            return False

        # Compound task → try each applicable method
        visited = visited | {task.name}
        methods = self._methods.get(task.name, [])
        if not methods:
            logger.warning("No methods for compound task '%s'", task.name)
            return False

        applicable = [
            m for m in methods
            if m.preconditions is None or m.preconditions(state)
        ]
        if not applicable:
            logger.debug("No applicable method for '%s'", task.name)
            return False

        for method in applicable:
            # Recursively decompose all sub-tasks
            subtask_plan: List[PlanningAction] = []
            success = True
            for sub in method.subtasks:
                if not self._decompose(sub, state, subtask_plan, visited, depth + 1):
                    success = False
                    break

            if success:
                plan.extend(subtask_plan)
                return True

        return False

    # ── diagnostics ──────────────────────────────────────────────────

    def get_stats(self) -> Dict[str, Any]:
        stats = super().get_stats()
        stats.update({
            "methods_registered": sum(len(v) for v in self._methods.values()),
            "primitives_registered": len(self._primitives),
        })
        return stats

