# Copyright (c) Ultrone Contributors. All rights reserved.
"""Verifier — checks whether a task's output satisfies its requirements.

The verifier turns a goal and a produced output into a pass/fail verdict with
a score and targeted feedback. It is backend-agnostic: verification can be
performed by a programmatic check function, a ``Verifier`` protocol, or a
solver-based LLM judge.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

from frontier.reasoning.base import Verification, Verifier

logger = logging.getLogger("Ultrone.Frontier.Agents.Verifier")


@dataclass
class VerificationResult:
    """The outcome of verifying a task output."""

    task: str
    output: Any
    passes: bool
    score: float = 0.0
    feedback: str = ""
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "task": self.task,
            "output": self.output,
            "passes": self.passes,
            "score": self.score,
            "feedback": self.feedback,
            "details": self.details,
        }


class Verifier:
    """Verifies task outputs against expectations.

    Parameters
    ----------
    check_fn : Optional[Callable]
        A programmatic callable ``(output, task, context) -> (passes, score, feedback)``.
    verifier : Optional[Verifier]
        A ``Verifier`` protocol instance (see ``frontier.reasoning.base``).
    solver : Optional[Callable]
        A solver used as an LLM judge for verification.
    oracle : Optional[Callable]
        An optional callable returning the ground-truth answer for a task.
    """

    def __init__(
        self,
        check_fn: Optional[Callable[..., Any]] = None,
        verifier: Optional[Verifier] = None,
        solver: Optional[Callable[[str], str]] = None,
        oracle: Optional[Callable[[str], Any]] = None,
    ) -> None:
        self._check_fn = check_fn
        self._verifier = verifier
        self._solver = solver
        self._oracle = oracle
        self._history: List[VerificationResult] = []

    def verify(
        self,
        task: str,
        output: Any,
        context: Optional[Dict[str, Any]] = None,
    ) -> VerificationResult:
        """Verify ``output`` for ``task``.

        Returns
        -------
        VerificationResult
            The verdict for the produced output.
        """
        context = context or {}

        # Priority: programmatic check > verifier protocol > oracle > solver.
        if self._check_fn is not None:
            passes, score, feedback = self._check_fn(output, task, context)
            result = VerificationResult(
                task=task, output=output, passes=bool(passes), score=float(score), feedback=str(feedback)
            )
        elif self._verifier is not None:
            verification = self._verifier(str(output), task)
            result = VerificationResult(
                task=task, output=output, passes=verification.passes,
                score=verification.score, feedback=verification.feedback,
                details=verification.details,
            )
        elif self._oracle is not None:
            expected = self._oracle(task)
            matched = str(expected).strip() in str(output).strip()
            result = VerificationResult(
                task=task, output=output, passes=matched,
                score=1.0 if matched else 0.0,
                feedback="Output matches expected answer." if matched else "Output does not match expected answer.",
            )
        elif self._solver is not None:
            result = self._solver_verify(task, output)
        else:
            result = VerificationResult(
                task=task, output=output, passes=False,
                score=0.0, feedback="No verifier configured.",
            )

        self._history.append(result)
        return result

    def _solver_verify(self, task: str, output: Any) -> VerificationResult:
        """Use a solver as an LLM judge to verify output."""
        prompt = (
            f"Task: {task}\n\nProduced output:\n{output}\n\n"
            f"Determine whether the output correctly satisfies the task. "
            f"Reply with: PASS or FAIL, then a brief reason."
        )
        raw = self._solver(prompt).strip()
        passes = raw.upper().startswith("PASS")
        return VerificationResult(
            task=task, output=output, passes=passes,
            score=1.0 if passes else 0.0, feedback=raw,
        )

    def get_history(self) -> List[VerificationResult]:
        """Return all verification results."""
        return list(self._history)

    def get_stats(self) -> Dict[str, Any]:
        """Return aggregate statistics."""
        if not self._history:
            return {"verifications": 0, "pass_rate": 0.0}
        passed = sum(1 for v in self._history if v.passes)
        return {
            "verifications": len(self._history),
            "pass_rate": passed / len(self._history),
        }
