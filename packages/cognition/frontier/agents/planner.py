# Copyright (c) Ultrone Contributors. All rights reserved.
"""Planner — decomposes a task into a sequence of executable steps.

The planner converts a high-level goal into a structured plan of steps. It is
backend-agnostic: planning is performed by a ``Solver`` (an LLM or test
double) or by an explicit plan generator callable. Plans are validated for
well-formedness and can be re-planned when execution fails.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

from frontier.reasoning.base import Solver

logger = logging.getLogger("Ultrone.Frontier.Agents.Planner")


@dataclass
class PlanStep:
    """A single step in a plan."""

    index: int
    description: str
    tool: str = ""
    args: Dict[str, Any] = field(default_factory=dict)
    dependencies: List[int] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "index": self.index,
            "description": self.description,
            "tool": self.tool,
            "args": self.args,
            "dependencies": self.dependencies,
        }


@dataclass
class Plan:
    """A structured multi-step plan."""

    goal: str
    steps: List[PlanStep] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {"goal": self.goal, "steps": [s.to_dict() for s in self.steps]}


class Planner:
    """Decomposes a task into executable steps.

    Parameters
    ----------
    solver : Optional[Solver]
        The backend solver used to generate the plan.
    plan_generator : Optional[Callable]
        An explicit callable ``(goal, context) -> List[PlanStep]``. If provided,
        it takes precedence over the solver.
    """

    def __init__(
        self,
        solver: Optional[Solver] = None,
        plan_generator: Optional[Callable[..., List[PlanStep]]] = None,
    ) -> None:
        self.solver = solver
        self._plan_generator = plan_generator
        self._history: List[Plan] = []

    def plan(self, goal: str, context: Optional[Dict[str, Any]] = None) -> Plan:
        """Generate a plan for ``goal``.

        Parameters
        ----------
        goal : str
            The high-level task to accomplish.
        context : Optional[Dict[str, Any]]
            Optional context (constraints, available tools, etc.).

        Returns
        -------
        Plan
            A validated plan with ordered steps.
        """
        context = context or {}
        if self._plan_generator is not None:
            steps = self._plan_generator(goal, context)
        elif self.solver is not None:
            steps = self._solver_plan(goal, context)
        else:
            steps = self._heuristic_plan(goal)

        plan = Plan(goal=goal, steps=self._validate(steps))
        self._history.append(plan)
        return plan

    def _solver_plan(self, goal: str, context: Dict[str, Any]) -> List[PlanStep]:
        """Use the solver to produce a structured plan."""
        tools = context.get("tools", [])
        tools_text = ", ".join(tools) if tools else "no specific tools"
        plan_prompt = (
            f"Create a step-by-step plan to accomplish the following goal:\n{goal}\n\n"
            f"Available tools: {tools_text}\n\n"
            f"Output one step per line in the format: STEP <n>: <description>"
        )
        raw = self.solver(plan_prompt)
        steps: List[PlanStep] = []
        for idx, line in enumerate(raw.splitlines()):
            stripped = line.strip()
            if not stripped:
                continue
            # Remove "STEP n: " prefix if present.
            desc = stripped
            if stripped.upper().startswith("STEP"):
                parts = stripped.split(":", 1)
                if len(parts) == 2:
                    desc = parts[1].strip()
            steps.append(PlanStep(index=idx, description=desc))
        return steps

    def _heuristic_plan(self, goal: str) -> List[PlanStep]:
        """Produce a basic plan when no solver is available."""
        return [
            PlanStep(index=0, description=f"Understand the goal: {goal}"),
            PlanStep(index=1, description="Gather required information and resources"),
            PlanStep(index=2, description="Execute the core work for the goal"),
            PlanStep(index=3, description="Verify the result against the goal"),
            PlanStep(index=4, description="Finalize and report"),
        ]

    def _validate(self, steps: List[PlanStep]) -> List[PlanStep]:
        """Validate and normalize plan steps."""
        validated: List[PlanStep] = []
        for idx, step in enumerate(steps):
            # Re-assign indices to be contiguous.
            step.index = idx
            validated.append(step)
        return validated

    def replan(
        self,
        goal: str,
        context: Dict[str, Any],
        failed_step_index: int,
        feedback: str,
    ) -> Plan:
        """Re-plan after a step fails during execution."""
        logger.info("Replanning after failure at step %d: %s", failed_step_index, feedback)
        context = dict(context)
        context["previous_failure"] = {
            "step_index": failed_step_index,
            "feedback": feedback,
        }
        return self.plan(goal, context)

    def get_history(self) -> List[Plan]:
        """Return all plans generated by this planner."""
        return list(self._history)

    def get_stats(self) -> Dict[str, Any]:
        """Return aggregate statistics."""
        return {
            "plans": len(self._history),
            "total_steps": sum(len(p.steps) for p in self._history),
        }
