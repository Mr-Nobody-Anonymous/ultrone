# Copyright (c) Ultrone Contributors. All rights reserved.
"""Constitutional Critique reasoning strategy.

Implements a Constitutional-AI-inspired generate → critique → revise loop
(grounded in Bai et al., 2022, "Constitutional AI: Harmlessness from AI
Feedback") adapted for correctness and reasoning quality.

The strategy:
1. Generates an initial solution from the solver.
2. Critiques the solution against a set of principles (the "constitution").
3. Revises the solution in light of the critique.
4. Repeats for a configurable number of rounds (or until no critique).

Unlike the self-correction engine, this is *principle-guided* rather than
grounded in an external verifier, so it is ideal for open-ended reasoning
where no programmatic checker exists.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

from .base import ReasoningResult, ReasoningStrategy, Solver

logger = logging.getLogger("Ultrone.Frontier.Reasoning.Constitutional")


# Default principles focus on correctness and reasoning quality, not safety
# only. These are generic and benchmark-agnostic.
DEFAULT_PRINCIPLES: List[str] = [
    "The reasoning must be logically sound with no unjustified jumps.",
    "Every numerical or factual claim must be accurate and verifiable.",
    "Edge cases and assumptions must be stated explicitly.",
    "The answer must directly address the question asked.",
    "The reasoning must be complete, leaving no important step unexplained.",
]


@dataclass
class ConstitutionalCritiqueConfig:
    """Configuration for the Constitutional Critique strategy."""

    max_rounds: int = 2
    temperature: float = 0.7
    principles: List[str] = field(default_factory=lambda: list(DEFAULT_PRINCIPLES))
    stop_on_clean: bool = True


class ConstitutionalCritique(ReasoningStrategy):
    """Constitutional Critique reasoning strategy.

    Parameters
    ----------
    solver : Optional[Solver]
        The backend solver used to generate and revise solutions.
    critic : Optional[Callable]
        Optional callable returning feedback for a solution given the
        principles. Defaults to an internal prompt-based critic.
    **config
        Overrides for :class:`ConstitutionalCritiqueConfig`.
    """

    def __init__(
        self,
        solver: Optional[Solver] = None,
        critic: Optional[Callable[..., str]] = None,
        **config: Any,
    ) -> None:
        super().__init__(solver=solver, **config)
        self.cfg = ConstitutionalCritiqueConfig(**{
            k: v for k, v in config.items() if hasattr(ConstitutionalCritiqueConfig, k)
        })
        self._critic = critic

    def strategy_name(self) -> str:
        return "constitutional_critique"

    def solve(self, prompt: str, **kwargs: Any) -> ReasoningResult:
        """Generate, critique, and revise a solution against principles."""
        if self.solver is None:
            raise ValueError("ConstitutionalCritique requires a solver")

        max_rounds = kwargs.get("max_rounds", self.cfg.max_rounds)
        solution = self.solver(prompt, temperature=self.cfg.temperature)
        steps: List[str] = ["Generated initial solution"]

        for round_num in range(1, max_rounds + 1):
            critique = self._critique(prompt, solution)
            if not critique.strip():
                steps.append(f"Round {round_num}: no critique; solution accepted")
                break
            steps.append(f"Round {round_num}: critique received — {critique.strip()[:80]}...")
            solution = self._revise(prompt, solution, critique)
            if self.cfg.stop_on_clean:
                # If the revised solution triggers no further critique, stop.
                next_critique = self._critique(prompt, solution)
                if not next_critique.strip():
                    steps.append(f"Round {round_num}: revised solution accepted")
                    break

        return ReasoningResult(
            solution=solution,
            confidence=0.8,
            metadata={"principles": len(self.cfg.principles), "steps": steps},
        )

    def _critique(self, prompt: str, solution: str) -> str:
        """Return critique feedback for ``solution`` against the principles."""
        if self._critic is not None:
            return self._critic(prompt, solution, self.cfg.principles)
        principles_text = "\n".join(f"- {p}" for p in self.cfg.principles)
        critique_prompt = (
            f"{prompt}\n\nCandidate solution:\n{solution}\n\n"
            f"Critique this solution against the following principles. List only "
            f"concrete problems, or reply 'OK' if all principles are satisfied.\n"
            f"{principles_text}"
        )
        return self.solver(critique_prompt, temperature=0.0).strip()

    def _revise(self, prompt: str, solution: str, critique: str) -> str:
        """Revise ``solution`` based on ``critique``."""
        revise_prompt = (
            f"{prompt}\n\nYour previous solution:\n{solution}\n\n"
            f"The following critique was given:\n{critique}\n\n"
            f"Produce a revised solution that addresses all critique points "
            f"while keeping what is correct."
        )
        return self.solver(revise_prompt, temperature=self.cfg.temperature).strip()
