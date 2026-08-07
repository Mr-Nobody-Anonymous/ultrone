# Copyright (c) Ultrone Contributors. All rights reserved.
"""Reflection Engine — generates, reflects, and improves solutions.

Implements the self-refine / reflection loop used in modern reasoning systems
(close in spirit to Shinn et al., 2023, "Reflexion" and Madaan et al., 2023,
"Self-Refine"). The engine:

1. Generates an initial solution.
2. Obtains feedback (from a critic or a verifier).
3. Reflects on the feedback to produce an improvement strategy.
4. Regenerates the solution guided by the reflection.

The engine is backend-agnostic (pluggable solver, critic, and verifier) and
records an auditable reflection trace.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

from frontier.reasoning.base import Solver, Verification, Verifier

from .critic_model import CriticModel, Critique

logger = logging.getLogger("Ultrone.Frontier.Adaptation.Reflection")


@dataclass
class ReflectionConfig:
    """Configuration for the Reflection Engine."""

    max_reflections: int = 3
    temperature: float = 0.7
    require_improvement: bool = True


@dataclass
class ReflectionTrace:
    """A record of one reflection iteration."""

    round: int
    solution: str
    feedback: str
    was_improvement: bool

    def to_dict(self) -> Dict[str, Any]:
        return {
            "round": self.round,
            "solution": self.solution,
            "feedback": self.feedback,
            "was_improvement": self.was_improvement,
        }


class ReflectionEngine:
    """Generates, reflects on, and improves solutions.

    Parameters
    ----------
    solver : Solver
        The backend solver for generating and regenerating solutions.
    critic : Optional[CriticModel]
        A critic used to evaluate each solution. If omitted, feedback falls
        back to a verifier or a generic prompt.
    verifier : Optional[Verifier]
        An optional programmatic verifier for scoring solutions.
    reflector : Optional[Callable]
        An explicit callable ``(prompt, solution, feedback) -> str`` producing
        a reflection/improvement guidance. Defaults to an internal prompt.
    **config
        Overrides for :class:`ReflectionConfig`.
    """

    def __init__(
        self,
        solver: Solver,
        critic: Optional[CriticModel] = None,
        verifier: Optional[Verifier] = None,
        reflector: Optional[Callable[..., str]] = None,
        **config: Any,
    ) -> None:
        self.solver = solver
        self.critic = critic or CriticModel(solver=solver)
        self.verifier = verifier
        self._reflector = reflector
        self.cfg = ReflectionConfig(**{
            k: v for k, v in config.items() if hasattr(ReflectionConfig, k)
        })
        self._traces: List[ReflectionTrace] = []

    def reflect(self, prompt: str, **kwargs: Any) -> Dict[str, Any]:
        """Run the reflection loop and return the final solution + trace.

        Returns a dict with ``solution``, ``rounds``, and ``traces``.
        """
        max_reflections = kwargs.get("max_reflections", self.cfg.max_reflections)
        solution = self.solver(prompt, temperature=self.cfg.temperature)
        best_solution = solution
        best_score = self._score(prompt, solution)
        traces: List[ReflectionTrace] = []

        for round_num in range(1, max_reflections + 1):
            feedback = self._feedback(prompt, solution)
            if not feedback.strip():
                traces.append(ReflectionTrace(round_num, solution, "No feedback", False))
                break

            reflection = self._reflect(prompt, solution, feedback)
            new_solution = self.solver(
                f"{prompt}\n\nPrevious solution:\n{solution}\n\n"
                f"Reflection / improvement guidance:\n{reflection}\n\n"
                f"Produce an improved solution.",
                temperature=self.cfg.temperature,
            )
            new_score = self._score(prompt, new_solution)
            was_improvement = new_score > best_score
            traces.append(ReflectionTrace(round_num, new_solution, feedback, was_improvement))

            if self.cfg.require_improvement:
                if was_improvement:
                    best_solution = new_solution
                    best_score = new_score
                    solution = new_solution
                else:
                    # No improvement this round; keep the best and stop.
                    break
            else:
                solution = new_solution
                best_solution = new_solution
                best_score = new_score

            if best_score >= 1.0:
                break

        self._traces.extend(traces)
        return {"solution": best_solution, "rounds": len(traces), "traces": traces}

    def _score(self, prompt: str, solution: str) -> float:
        """Score a solution using the verifier (preferred) or critic."""
        if self.verifier is not None:
            verification = self.verifier(solution, prompt)
            return verification.score
        return self.critic.evaluate(prompt, solution).score

    def _feedback(self, prompt: str, solution: str) -> str:
        """Obtain feedback for a solution."""
        critique = self.critic.evaluate(prompt, solution)
        parts = []
        if critique.issues:
            parts.append("Issues:\n" + "\n".join(f"- {i}" for i in critique.issues))
        if critique.suggestions:
            parts.append("Suggestions:\n" + "\n".join(f"- {s}" for s in critique.suggestions))
        if not parts:
            return "The solution appears correct."
        return "\n".join(parts)

    def _reflect(self, prompt: str, solution: str, feedback: str) -> str:
        """Produce a reflection guiding how to improve the solution."""
        if self._reflector is not None:
            return self._reflector(prompt, solution, feedback)
        reflect_prompt = (
            f"{prompt}\n\nCurrent solution:\n{solution}\n\n"
            f"Feedback:\n{feedback}\n\n"
            f"Reflect on what went wrong and how to fix it. Provide a concise "
            f"step-by-step improvement plan."
        )
        return self.solver(reflect_prompt, temperature=self.cfg.temperature).strip()

    def get_traces(self) -> List[ReflectionTrace]:
        """Return all reflection traces produced by this engine."""
        return list(self._traces)

    def get_stats(self) -> Dict[str, Any]:
        """Return aggregate statistics."""
        return {
            "reflections_run": len(self._traces),
            "max_reflections": self.cfg.max_reflections,
            "critic": self.critic.get_stats(),
        }
