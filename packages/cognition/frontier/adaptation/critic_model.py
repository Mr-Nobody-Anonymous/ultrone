# Copyright (c) Ultrone Contributors. All rights reserved.
"""Critic Model — evaluates and critiques proposed solutions.

A pluggable critic that scores a solution for a given prompt and produces
targeted, actionable feedback. Used by the reflection and self-correction
engines and by constitutional critique.

The critic is backend-agnostic: it wraps a ``Solver`` (an LLM or test double)
or accepts an explicit critic callable. It never hardcodes benchmark answers.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger("Ultrone.Frontier.Adaptation.Critic")


@dataclass
class Critique:
    """The output of a critic evaluation."""

    score: float = 0.5
    issues: List[str] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)
    passed: bool = False
    summary: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "score": self.score,
            "issues": self.issues,
            "suggestions": self.suggestions,
            "passed": self.passed,
            "summary": self.summary,
        }


class CriticModel:
    """A pluggable critic for evaluating solutions.

    Parameters
    ----------
    solver : Optional[Callable]
        A callable ``(prompt) -> str`` used to generate the critique. If
        omitted, a heuristic scorer is used.
    threshold : float
        The score at or above which a solution is considered to have passed.
    critic_fn : Optional[Callable]
        An explicit callable ``(prompt, solution) -> Critique``. If provided,
        it takes precedence over the solver.
    """

    def __init__(
        self,
        solver: Optional[Callable[[str], str]] = None,
        threshold: float = 0.6,
        critic_fn: Optional[Callable[[str, str], "Critique"]] = None,
    ) -> None:
        self.solver = solver
        self.threshold = threshold
        self._critic_fn = critic_fn
        self._history: List[Critique] = []

    def evaluate(self, prompt: str, solution: str) -> Critique:
        """Evaluate ``solution`` and return a :class:`Critique`."""
        if self._critic_fn is not None:
            critique = self._critic_fn(prompt, solution)
        elif self.solver is not None:
            critique = self._solver_critique(prompt, solution)
        else:
            critique = self._heuristic_critique(prompt, solution)

        critique.passed = critique.score >= self.threshold
        self._history.append(critique)
        return critique

    def _solver_critique(self, prompt: str, solution: str) -> Critique:
        """Use the solver to produce a structured critique."""
        critic_prompt = (
            f"{prompt}\n\nCandidate solution:\n{solution}\n\n"
            f"Evaluate this solution. Provide a response with three sections:\n"
            f"Score: <0.0 to 1.0>\n"
            f"Issues:\n- <issue 1>\n- <issue 2>\n"
            f"Suggestions:\n- <suggestion 1>\n- <suggestion 2>"
        )
        raw = self.solver(critic_prompt)
        return self._parse_critique(raw)

    def _heuristic_critique(self, prompt: str, solution: str) -> Critique:
        """Produce a basic heuristic critique when no solver is available."""
        issues: List[str] = []
        suggestions: List[str] = []

        if not solution.strip():
            issues.append("Solution is empty.")
            suggestions.append("Provide a substantive solution.")
            return Critique(score=0.0, issues=issues, suggestions=suggestions, summary="Empty solution")

        # Length-based heuristic: extremely short solutions are often incomplete.
        length = len(solution.strip())
        base_score = 0.5
        if length < 20:
            issues.append("Solution is very short and may be incomplete.")
            suggestions.append("Expand the solution and explain the reasoning steps.")
            base_score -= 0.2
        elif length > 200:
            base_score += 0.1

        if "error" in solution.lower() or "incorrect" in solution.lower():
            issues.append("Solution contains self-referential error language.")
            suggestions.append("Verify correctness and remove hedging language.")

        score = max(0.0, min(1.0, base_score))
        return Critique(
            score=score,
            issues=issues,
            suggestions=suggestions,
            summary="Heuristic critique",
        )

    def _parse_critique(self, raw: str) -> Critique:
        """Parse a solver's critique text into a :class:`Critique`."""
        issues: List[str] = []
        suggestions: List[str] = []
        score = 0.5

        in_issues = False
        in_suggestions = False
        for line in raw.splitlines():
            stripped = line.strip()
            lower = stripped.lower()
            if lower.startswith("score"):
                try:
                    num = "".join(ch for ch in stripped.split(":")[-1] if ch.isdigit() or ch == ".")
                    score = max(0.0, min(1.0, float(num)))
                except ValueError:
                    pass
            elif lower.startswith("issue"):
                in_issues = True
                in_suggestions = False
            elif lower.startswith("suggestion"):
                in_suggestions = True
                in_issues = False
            elif stripped.startswith("-") and in_issues:
                issues.append(stripped.lstrip("- ").strip())
            elif stripped.startswith("-") and in_suggestions:
                suggestions.append(stripped.lstrip("- ").strip())

        return Critique(
            score=score,
            issues=issues,
            suggestions=suggestions,
            summary=raw.strip()[:120],
        )

    def get_history(self) -> List[Critique]:
        """Return all critiques produced by this critic."""
        return list(self._history)

    def get_stats(self) -> Dict[str, Any]:
        """Return aggregate statistics."""
        if not self._history:
            return {"critiques": 0, "avg_score": 0.0, "pass_rate": 0.0}
        scores = [c.score for c in self._history]
        passed = sum(1 for c in self._history if c.passed)
        return {
            "critiques": len(self._history),
            "avg_score": sum(scores) / len(scores),
            "pass_rate": passed / len(self._history),
        }
        
