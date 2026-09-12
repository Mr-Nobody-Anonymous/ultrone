# Copyright (c) Ultrone Contributors. All rights reserved.
"""Self-Correction Engine — retries and corrects solutions until verified.

Implements a verification-grounded correction loop. Unlike the reflection
engine (which relies on a critic/LLM feedback), the self-correction engine
drives improvement using a programmatic :class:`Verifier`:

1. Generate a solution.
2. Verify it. If it passes, accept it.
3. If it fails, feed the verification feedback back into the solver to
   correct the solution.
4. Repeat up to ``max_attempts``.

This is the backbone of verifiable, tool-using agents (e.g. code execution
feedback) and is pivotal for SWE-bench / HumanEval style tasks.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from frontier.reasoning.base import Solver, Verification, Verifier

logger = logging.getLogger("Ultrone.Frontier.Adaptation.SelfCorrection")


@dataclass
class SelfCorrectionConfig:
    """Configuration for the Self-Correction Engine."""

    max_attempts: int = 3
    temperature: float = 0.7
    accept_score: float = 1.0


@dataclass
class CorrectionAttempt:
    """A record of one correction attempt."""

    attempt: int
    solution: str
    verification: Verification

    def to_dict(self) -> Dict[str, Any]:
        return {
            "attempt": self.attempt,
            "solution": self.solution,
            "passes": self.verification.passes,
            "score": self.verification.score,
            "feedback": self.verification.feedback,
        }


class SelfCorrectionEngine:
    """Verification-grounded self-correction loop.

    Parameters
    ----------
    solver : Solver
        The backend solver used to generate and correct solutions.
    verifier : Verifier
        The programmatic verifier used to check solutions.
    **config
        Overrides for :class:`SelfCorrectionConfig`.
    """

    def __init__(
        self,
        solver: Solver,
        verifier: Verifier,
        **config: Any,
    ) -> None:
        self.solver = solver
        self.verifier = verifier
        self.cfg = SelfCorrectionConfig(**{
            k: v for k, v in config.items() if hasattr(SelfCorrectionConfig, k)
        })
        self._attempts: List[CorrectionAttempt] = []

    def solve(self, prompt: str, **kwargs: Any) -> Dict[str, Any]:
        """Run the self-correction loop for ``prompt``.

        Returns a dict with ``solution``, ``passed``, ``score``, and ``attempts``.
        """
        max_attempts = kwargs.get("max_attempts", self.cfg.max_attempts)
        solution = self.solver(prompt, temperature=self.cfg.temperature)
        attempts: List[CorrectionAttempt] = []

        for attempt in range(1, max_attempts + 1):
            verification = self.verifier(solution, prompt)
            attempts.append(CorrectionAttempt(attempt, solution, verification))

            if verification.passes or verification.score >= self.cfg.accept_score:
                logger.info("Solution accepted on attempt %d", attempt)
                break

            # Correct the solution using verification feedback.
            if attempt < max_attempts:
                solution = self._correct(prompt, solution, verification)

        self._attempts.extend(attempts)
        final = attempts[-1]
        return {
            "solution": final.solution,
            "passed": final.verification.passes,
            "score": final.verification.score,
            "attempts": attempts,
        }

    def _correct(self, prompt: str, solution: str, verification: Verification) -> str:
        """Correct a solution based on verification feedback."""
        feedback = verification.feedback or "The solution is incorrect. Please fix it."
        correct_prompt = (
            f"{prompt}\n\nYour previous solution:\n{solution}\n\n"
            f"Verification feedback:\n{feedback}\n\n"
            f"Produce a corrected solution that addresses the feedback."
        )
        return self.solver(correct_prompt, temperature=self.cfg.temperature).strip()

    def get_attempts(self) -> List[CorrectionAttempt]:
        """Return all correction attempts produced by this engine."""
        return list(self._attempts)

    def get_stats(self) -> Dict[str, Any]:
        """Return aggregate statistics."""
        if not self._attempts:
            return {"runs": 0, "success_rate": 0.0, "avg_attempts": 0.0}
        runs = len(self._attempts)
        successes = sum(1 for a in self._attempts if a.verification.passes)
        return {
            "runs": runs,
            "success_rate": successes / runs,
            "avg_attempts": self.cfg.max_attempts,
        }
