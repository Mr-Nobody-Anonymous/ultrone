# Copyright (c) Ultrone Contributors. All rights reserved.
"""Hierarchical Task Network (HTN) planner.

HTN decomposes high-level tasks into primitive actions using
methods and domain knowledge.  It is effective for structured
military operations where standard operating procedures (SOPs)
are well-defined.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple

from .base import Planner, PlanningAction, PlanningDomain, PlanningGoal, PlanningResult

logger = logging.getLogger("Ultrone.Brain.Reasoning.Search.HTN")


@dataclass
class HTNConfig:
    """Configuration for HTN."""
    max_decomposition_depth: int = 20
    max_branching: int = 10


@dataclass
class Task:
    """A task in the HTN hierarchy."""
    name: str
    is_primitive: bool = False
    parameters: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Method:
    """A method decomposes a compound task into subtasks."""
    task_name: str
    subtasks: List[Task]
    preconditions: Optional[Callable[[Dict[str, Any]], bool]] = None


class PrimitiveTask(Task):
    """A primitive (executable) task."""
    def __init__(self, name: str, action: Optional[PlanningAction] = None,
                 preconditions: Optional[Callable] = None,
                 effects: Optional[Callable] = None,
                 parameters: Optional[Dict[str, Any]] = None):
        super().__init__(name, is_primitive=True, parameters=parameters or {})
        self.action = action or PlanningAction(name)
        self.preconditions = preconditions
        self.effects = effects


class CompoundTask(Task):
    """A compound (decomposable) task."""
    def __init__(self, name: str, methods: Optional[List[Method]] = None,
                 parameters: Optional[Dict[str, Any]] = None):
        super().__init__(name, is_primitive=False, parameters=parameters or {})
        self.methods = methods or []


class HTNPlanner(Planner):
    """HTN planner that decomposes tasks hierarchically."""

    def __init__(self, config: Optional[HTNConfig] = None) -> None:
        super().__init__()
        self.config = config or HTNConfig()
        self._methods: Dict[str, List[Method]] = {}
        self._primitives: Dict[str, PrimitiveTask] = {}
        self._domain_knowledge: Dict[str, Any] = {}

    def add_method(self, method: Method) -> None:
        self._methods.setdefault(method.task_name, []).append(method)

    def add_primitive(self, task: PrimitiveTask) -> None:
        self._primitives[task.name] = task

    def initialize(self, domain: PlanningDomain) -> None:
        super().initialize(domain)

    def _decompose(self, task: Task, state: Any, depth: int) -> Optional[List[PlanningAction]]:
        """Decompose a task into actions."""
        if depth > self.config.max_decomposition_depth:
            return None

        if task.is_primitive:
            primitive = self._primitives.get(task.name)
            if primitive:
                return [primitive.action or PlanningAction(task.name)]
            return [PlanningAction(task.name)]

        # Compound task: find applicable method
        methods = self._methods.get(task.name, [])
        for method in methods[:self.config.max_branching]:
            if method.preconditions and not method.preconditions({"state": state}):
                continue
            plan: List[PlanningAction] = []
            for subtask in method.subtasks:
                subplan = self._decompose(subtask, state, depth + 1)
                if subplan is None:
                    break
                plan.extend(subplan)
            else:
                return plan
        return None

    def plan(self, state: Any, goal: PlanningGoal) -> PlanningResult:
        tasks = goal.predicates.get("tasks", [])
        if not tasks:
            tasks = [Task("plan", parameters={"goal": goal.description})]

        all_actions: List[PlanningAction] = []
        for task in tasks:
            actions = self._decompose(task, state, 0)
            if actions is None:
                result = PlanningResult(success=False, cost=float("inf"))
                logger.info("HTN plan FAILED: could not decompose %s", task.name)
                return self._record_result(result)
            all_actions.extend(actions)

        result = PlanningResult(
            success=True,
            actions=all_actions,
            cost=len(all_actions),
            plan_length=len(all_actions),
        )
        logger.info("HTN plan found: %d actions", result.plan_length)
        return self._record_result(result)
