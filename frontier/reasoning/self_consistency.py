# Copyright (c) Ultrone Contributors. All rights reserved.
"""Self-Consistency reasoning strategy.

Implements the Self-Consistency approach from Wang et al. (2022,
"Self-Consistency Improves Chain of Thought Reasoning in Language Models")
as a pluggable :class:`ReasoningStrategy`.

The strategy:
1. Samples ``n_samples`` independent solutions from the solver.
2. Optionally uses a verifier to score each candidate.
3. Aggregates the candidates into a final answer via majority voting
   (or confidence-weighted voting when a verifier is present).

This is backend-agnostic: the solver may be an LLM or a test double, and no
benchmark answers are hardcoded.
"""

from __future__ import annotations

import logging
from collections import Counter
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

from .base import ReasoningResult, ReasoningStrategy, Solver, Verifier

logger = logging.getLogger("Ultrone.Frontier.Reasoning.SelfConsistency")


@dataclass
class SelfConsistencyConfig:
    """Configuration for the Self-Consistency strategy."""

    n_samples: int = 5
    temperature: float = 0.7
    weighting: str = "uniform"  # "uniform" or "verifier"
    answer_key: Callable[[str], str] = staticmethod(lambda s: s.strip())


class SelfConsistency(ReasoningStrategy):
    """Self-Consistency reasoning strategy.

    Parameters
    ----------
    solver : Optional[Solver]
        The backend solver used to sample multiple solutions.
    verifier : Optional[Verifier]
        Optional verifier scoring each candidate for weighted voting.
    answer_extractor : Optional[Callable[[str], str]]
        Optional callable mapping a raw solution to a canonical answer key for
        voting. Defaults to stripping whitespace.
    **config
        Overrides for :class:`SelfConsistencyConfig`.
    """

    def __init__(
        self,
        solver: Optional[Solver] = None,
        verifier: Optional[Verifier] = None,
        answer_extractor: Optional[Callable[[str], str]] = None,
        **config: Any,
    ) -> None:
        super().__init__(solver=solver, **config)
        cfg_defaults = {
            "n_samples": 5,
            "temperature": 0.7,
            "weighting": "uniform",
        }
        cfg_defaults.update(config)
        self.cfg = SelfConsistencyConfig(**cfg_defaults)
        self.verifier = verifier
        self._answer_extractor = answer_extractor or self.cfg.answer_key

    def strategy_name(self) -> str:
        return "self_consistency"

    def solve(self, prompt: str, **kwargs: Any) -> ReasoningResult:
        """Solve ``prompt`` by sampling and aggregating multiple solutions."""
        if self.solver is None:
            raise ValueError("SelfConsistency requires a solver")

        n_samples = kwargs.get("n_samples", self.cfg.n_samples)
        temperature = kwargs.get("temperature", self.cfg.temperature)

        candidates: List[str] = []
        scores: List[float] = []
        for _ in range(n_samples):
            solution = self.solver(prompt, temperature=temperature)
            candidates.append(solution)
            if self.verifier is not None:
                verification = self.verifier(solution, prompt)
                scores.append(verification.score)
            else:
                scores.append(1.0)

        # Aggregate via voting.
        final_answer, confidence, votes = self._aggregate(candidates, scores)

        steps = [
            f"Sampled {len(candidates)} solutions",
            f"Voted {len({self._answer_extractor(c) for c in candidates})} distinct answers",
            f"Chosen answer with {confidence:.2f} confidence",
        ]

        return ReasoningResult(
            solution=final_answer,
            confidence=confidence,
            candidates=list(candidates),
            metadata={"n_samples": len(candidates), "votes": votes, "steps": steps},
        )

    def _aggregate(self, candidates: List[str], scores: List[float]) -> "tuple[str, float, dict]":
        """Aggregate candidate solutions into a final answer.

        Returns a ``(final_answer, confidence, votes)`` tuple where ``votes``
        maps each answer key to its aggregated weight.
        """
        if self.cfg.weighting == "verifier" and self.verifier is not None:
            # Confidence-weighted voting.
            tally: Dict[str, float] = Counter()
            for cand, score in zip(candidates, scores):
                tally[self._answer_extractor(cand)] += score
            total = sum(tally.values()) or 1.0
            best_key = max(tally, key=tally.get)
            best_votes = tally[best_key]
            return best_key, best_votes / total, dict(tally)

        # Uniform majority voting.
        tally = Counter(self._answer_extractor(c) for c in candidates)
        total = len(candidates)
        best_key = max(tally, key=tally.get)
        best_votes = tally[best_key]
        return best_key, best_votes / total, dict(tally)
