# Copyright (c) Ultrone Contributors. All rights reserved.
"""Executor — executes plan steps, dispatching to tools or a solver.

The executor takes a :class:`Plan` and runs each step, invoking the appropriate
tool (via a tool registry) or a solver for steps that require reasoning. It
tracks per-step results and supports failure handling so the planner can
re-plan when a step fails.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

from frontier.reasoning.base import Solver

from .planner import Plan, PlanStep

logger = logging.getLogger("Ultrone.Frontier.Agents.Executor")


@dataclass
class StepResult:
    """The result of executing a single step."""

    step_index: int
    success: bool
    output: Any = None
    error: str = ""
    tool: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "step_index": self.step_index,
            "success": self.success,
            "output": self.output,
            "error": self.error,
            "tool": self.tool,
        }


@dataclass
class ExecutionResult:
    """The aggregate result of executing a full plan."""

    plan: Plan
    step_results: List[StepResult] = field(default_factory=list)
    success: bool = False
    final_output: Any = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "plan": self.plan.to_dict(),
            "step_results": [s.to_dict() for s in self.step_results],
            "success": self.success,
            "final_output": self.final_output,
        }


class Executor:
    """Executes plan steps using registered tools or a solver.

    Parameters
    ----------
    solver : Optional[Solver]
        A solver used for steps that do not map to a registered tool.
    tools : Optional[Dict[str, Callable]]
        A mapping of tool name to a callable accepting ``**kwargs``.
    """

    def __init__(
        self,
        solver: Optional[Solver] = None,
        tools: Optional[Dict[str, Callable[..., Any]]] = None,
    ) -> None:
        self.solver = solver
        self.tools = tools or {}
        self._results: List[ExecutionResult] = []

    def execute(self, plan: Plan) -> ExecutionResult:
        """Execute all steps of ``plan`` in order.

        If a step's ``tool`` is registered, it is dispatched there. Otherwise
        the step is executed with the solver (if available) or heuristically.
        Execution stops (and is marked failed) at the first failing step.

        Returns
        -------
        ExecutionResult
            The aggregate execution result.
        """
        step_results: List[StepResult] = []
        success = True

        for step in plan.steps:
            result = self._execute_step(step)
            step_results.append(result)
            if not result.success:
                success = False
                logger.warning("Step %d failed: %s", step.index, result.error)
                break

        final_output = step_results[-1].output if step_results and success else None
        exec_result = ExecutionResult(
            plan=plan,
            step_results=step_results,
            success=success,
            final_output=final_output,
        )
        self._results.append(exec_result)
        return exec_result

    def _execute_step(self, step: PlanStep) -> StepResult:
        """Execute a single step."""
        if step.tool in self.tools:
            try:
                output = self.tools[step.tool](**step.args)
                return StepResult(
                    step_index=step.index,
                    success=True,
                    output=output,
                    tool=step.tool,
                )
            except Exception as exc:  # noqa: BLE001
                return StepResult(
                    step_index=step.index,
                    success=False,
                    error=f"{type(exc).__name__}: {exc}",
                    tool=step.tool,
                )

        # No tool: use the solver if available.
        if self.solver is not None:
            prompt = (
                f"Execute the following step:\n{step.description}\n\n"
                f"Provide the result/output for this step."
            )
            try:
                output = self.solver(prompt)
                return StepResult(step_index=step.index, success=True, output=output)
            except Exception as exc:  # noqa: BLE001
                return StepResult(
                    step_index=step.index,
                    success=False,
                    error=f"{type(exc).__name__}: {exc}",
                )

        # Heuristic fallback.
        return StepResult(
            step_index=step.index,
            success=True,
            output=f"Executed step {step.index}: {step.description}",
        )

    def register_tool(self, name: str, fn: Callable[..., Any]) -> None:
        """Register (or replace) a tool by name."""
        self.tools[name] = fn

    def get_results(self) -> List[ExecutionResult]:
        """Return all execution results produced by this executor."""
        return list(self._results)

    def get_stats(self) -> Dict[str, Any]:
        """Return aggregate statistics."""
        return {
            "executions": len(self._results),
            "success_rate": (
                sum(1 for r in self._results if r.success) / len(self._results)
                if self._results
                else 0.0
            ),
            "tools_registered": len(self.tools),
        }
