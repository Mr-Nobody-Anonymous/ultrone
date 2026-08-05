# Copyright (c) Ultrone Contributors. All rights reserved.
"""Constitutional Critique — self-improvement through constitutional principles.

Implements constitutional AI principles where responses are critiqued
against a set of principles and revised accordingly.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger("Ultrone.AI.Reasoning.Constitutional")


@dataclass
class CritiqueConfig:
    """Configuration for constitutional critique."""
    principles: List[str] = field(default_factory=lambda: [
        "Be accurate and factual",
        "Be helpful and harmless",
        "Be concise and clear",
        "Consider edge cases",
        "Verify assumptions",
    ])
    max_revision_rounds: int = 3
    critique_threshold: float = 0.6
    enable_self_critique: bool = True


@dataclass
class CritiqueResult:
    """Result of a critique."""
    principle: str = ""
    score: float = 0.0
    critique: str = ""
    suggestion: str = ""


class ConstitutionalCritique:
    """Constitutional critique reasoning engine.

    Parameters
    ----------
    config : CritiqueConfig
        Configuration with principles.
    answer_generator : callable, optional
        Function that generates an initial answer.
    critic : callable, optional
        Function that critiques an answer against principles.
    reviser : callable, optional
        Function that revises an answer based on critiques.
    """

    def __init__(
        self,
        config: Optional[CritiqueConfig] = None,
        answer_generator: Optional[Callable[[str], str]] = None,
        critic: Optional[Callable[[str, str], CritiqueResult]] = None,
        reviser: Optional[Callable[[str, List[CritiqueResult]], str]] = None,
    ):
        self.config = config or CritiqueConfig()
        self._answer_generator = answer_generator or self._default_answer_generator
        self._critic = critic or self._default_critic
        self._reviser = reviser or self._default_reviser
        self._revision_history: List[Dict[str, Any]] = []

    def solve(self, problem: str) -> Dict[str, Any]:
        """Solve a problem with constitutional critique."""
        self._revision_history = []

        # Generate initial answer
        answer = self._answer_generator(problem)
        self._revision_history.append({"round": 0, "answer": answer, "critiques": []})

        # Iteratively critique and revise
        for round_num in range(1, self.config.max_revision_rounds + 1):
            # Critique against all principles
            critiques = []
            for principle in self.config.principles:
                result = self._critic(answer, principle)
                critiques.append(result)

            # Check if answer passes all principles
            avg_score = sum(c.score for c in critiques) / len(critiques) if critiques else 0.0
            if avg_score >= self.config.critique_threshold:
                break

            # Revise based on critiques
            answer = self._reviser(answer, critiques)
            self._revision_history.append({
                "round": round_num,
                "answer": answer,
                "critiques": [{"principle": c.principle, "score": c.score, "critique": c.critique} for c in critiques],
                "avg_score": avg_score,
            })

        final_score = self._revision_history[-1].get("avg_score", 0.5)
        return {
            "solved": final_score >= self.config.critique_threshold,
            "answer": answer,
            "confidence": final_score,
            "rounds": len(self._revision_history) - 1,
            "principles": len(self.config.principles),
            "revision_history": self._revision_history,
        }

    def _default_answer_generator(self, problem: str) -> str:
        return f"Initial answer to: {problem[:100]}"

    def _default_critic(self, answer: str, principle: str) -> CritiqueResult:
        score = min(1.0, 0.5 + len(answer) / 500)
        return CritiqueResult(
            principle=principle,
            score=score,
            critique=f"Answer could better adhere to: {principle}",
            suggestion=f"Consider {principle.lower()} more carefully",
        )

    def _default_reviser(self, answer: str, critiques: List[CritiqueResult]) -> str:
        suggestions = " ".join(c.suggestion for c in critiques[:3])
        return f"Revised: {answer} (Addressing: {suggestions})"

    def get_revision_history(self) -> List[Dict[str, Any]]:
        return self._revision_history