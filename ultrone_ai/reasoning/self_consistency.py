# Copyright (c) Ultrone Contributors. All rights reserved.
"""Self-Consistency Voting — sample multiple reasoning paths and vote.

Implements self-consistency from "Self-Consistency Improves Chain of Thought
Reasoning in Language Models" (Wang et al., 2022).

Generates multiple independent reasoning paths and selects the most
consistent answer via majority voting.
"""

from __future__ import annotations

import logging
import re
from collections import Counter
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger("Ultrone.AI.Reasoning.SelfConsistency")


@dataclass
class ConsistencyConfig:
    """Configuration for self-consistency voting."""
    num_samples: int = 5
    temperature: float = 0.7  # Higher temperature for diversity
    voting_method: str = "majority"  # majority, weighted, marginal
    answer_extractor: str = "auto"  # auto, regex, last_line


@dataclass
class ReasoningPath:
    """A single reasoning path."""
    path_id: int = 0
    reasoning: str = ""
    answer: str = ""
    confidence: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


class SelfConsistencyVoting:
    """Self-consistency voting reasoning engine.

    Parameters
    ----------
    config : ConsistencyConfig
        Configuration.
    reasoning_generator : callable, optional
        Function that generates a reasoning path: (problem: str) -> str
    answer_extractor : callable, optional
        Function that extracts the answer from reasoning: (reasoning: str) -> str
    """

    def __init__(
        self,
        config: Optional[ConsistencyConfig] = None,
        reasoning_generator: Optional[Callable[[str], str]] = None,
        answer_extractor: Optional[Callable[[str], str]] = None,
    ):
        self.config = config or ConsistencyConfig()
        self._reasoning_generator = reasoning_generator or self._default_reasoning_generator
        self._answer_extractor = answer_extractor or self._default_answer_extractor
        self._paths: List[ReasoningPath] = []

    def solve(self, problem: str) -> Dict[str, Any]:
        """Solve a problem using self-consistency voting."""
        self._paths = []

        # Generate multiple reasoning paths
        for i in range(self.config.num_samples):
            reasoning = self._reasoning_generator(problem)
            answer = self._answer_extractor(reasoning)
            path = ReasoningPath(
                path_id=i,
                reasoning=reasoning,
                answer=answer,
                confidence=self._compute_confidence(reasoning),
            )
            self._paths.append(path)

        # Vote on the best answer
        result = self._vote()

        return result

    def _vote(self) -> Dict[str, Any]:
        """Vote on the best answer from all paths."""
        if not self._paths:
            return {"solved": False, "answer": "", "confidence": 0.0, "paths": 0}

        if self.config.voting_method == "majority":
            return self._majority_vote()
        elif self.config.voting_method == "weighted":
            return self._weighted_vote()
        else:
            return self._marginal_vote()

    def _majority_vote(self) -> Dict[str, Any]:
        """Majority voting — most common answer wins."""
        answers = [p.answer for p in self._paths if p.answer]
        if not answers:
            best = max(self._paths, key=lambda p: p.confidence)
            return {
                "solved": False,
                "answer": best.answer,
                "confidence": best.confidence,
                "paths": len(self._paths),
                "agreement": 0.0,
            }

        counter = Counter(answers)
        best_answer, count = counter.most_common(1)[0]
        agreement = count / len(answers)

        # Average confidence of paths that agree
        agreeing_paths = [p for p in self._paths if p.answer == best_answer]
        avg_confidence = sum(p.confidence for p in agreeing_paths) / len(agreeing_paths)

        return {
            "solved": agreement > 0.5,
            "answer": best_answer,
            "confidence": avg_confidence * agreement,
            "paths": len(self._paths),
            "agreement": agreement,
            "vote_distribution": dict(counter),
        }

    def _weighted_vote(self) -> Dict[str, Any]:
        """Weighted voting — answers weighted by path confidence."""
        answer_scores: Dict[str, float] = {}
        for path in self._paths:
            if path.answer:
                answer_scores[path.answer] = answer_scores.get(path.answer, 0.0) + path.confidence

        if not answer_scores:
            return {"solved": False, "answer": "", "confidence": 0.0, "paths": len(self._paths)}

        best_answer = max(answer_scores, key=answer_scores.get)
        total_score = sum(answer_scores.values())
        confidence = answer_scores[best_answer] / total_score if total_score > 0 else 0.0

        return {
            "solved": confidence > 0.5,
            "answer": best_answer,
            "confidence": confidence,
            "paths": len(self._paths),
            "answer_scores": answer_scores,
        }

    def _marginal_vote(self) -> Dict[str, Any]:
        """Marginal voting — considers marginal confidence."""
        # Similar to weighted but normalizes per-path
        return self._weighted_vote()

    def _compute_confidence(self, reasoning: str) -> float:
        """Compute confidence for a reasoning path."""
        if not reasoning:
            return 0.0
        # Simple heuristic: longer reasoning with solution patterns
        score = min(1.0, 0.3 + len(reasoning) / 500)
        patterns = ["therefore", "thus", "so the answer", "the answer is"]
        for p in patterns:
            if p in reasoning.lower():
                score += 0.2
                break
        return min(1.0, score)

    def _default_reasoning_generator(self, problem: str) -> str:
        return f"Analyzing: {problem}\nTherefore, the answer is computed."

    def _default_answer_extractor(self, reasoning: str) -> str:
        """Extract the answer from a reasoning path."""
        # Try common patterns
        patterns = [
            r"the answer is[:\s]+(.+?)(?:\.|$)",
            r"final answer[:\s]+(.+?)(?:\.|$)",
            r"answer[:\s]*=[:\s]*(.+?)(?:\.|$)",
            r"result[:\s]+(.+?)(?:\.|$)",
            r"therefore[:\s]+(.+?)(?:\.|$)",
        ]
        for pattern in patterns:
            match = re.search(pattern, reasoning, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        # Fallback: last non-empty line
        lines = [l.strip() for l in reasoning.strip().split("\n") if l.strip()]
        return lines[-1] if lines else ""

    def get_paths(self) -> List[ReasoningPath]:
        return self._paths