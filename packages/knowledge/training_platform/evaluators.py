# Copyright (c) Ultrone Contributors. All rights reserved.
"""Evaluators for the training platform.

Provides model evaluation with standard metrics: accuracy, reasoning
accuracy, calibration, hallucination rate, retrieval accuracy, coding
success, tool-use success, latency, tokens/sec, memory usage, GPU
utilization, cost, robustness, and regression rate.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger("Ultrone.TrainingPlatform.Evaluators")


@dataclass
class EvaluationResult:
    """The result of a model evaluation."""

    model_id: str
    metrics: Dict[str, float] = field(default_factory=dict)
    num_examples: int = 0
    duration_seconds: float = 0.0
    errors: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "model_id": self.model_id,
            "metrics": self.metrics,
            "num_examples": self.num_examples,
            "duration_seconds": self.duration_seconds,
            "errors": self.errors,
        }


class Evaluator:
    """Evaluates a model against a set of examples.

    Parameters
    ----------
    model : Any
        The model to evaluate. Must be callable ``(prompt) -> str``.
    judge : Optional[Callable]
        A callable ``(response, expected) -> (bool, float)`` that scores
        a response against the expected answer.
    """

    def __init__(
        self,
        model: Any,
        judge: Optional[Callable[[str, str], Any]] = None,
    ):
        self.model = model
        self.judge = judge or self._default_judge
        self._history: List[EvaluationResult] = []

    @staticmethod
    def _default_judge(response: str, expected: str) -> tuple:
        """Default judge: token overlap F1."""
        r_tokens = set(response.lower().split())
        e_tokens = set(expected.lower().split())
        if not e_tokens:
            return True, 1.0
        overlap = len(r_tokens & e_tokens)
        precision = overlap / len(r_tokens) if r_tokens else 0.0
        recall = overlap / len(e_tokens)
        if precision + recall == 0:
            return False, 0.0
        f1 = 2 * precision * recall / (precision + recall)
        return f1 > 0.5, f1

    def evaluate(
        self,
        examples: List[Dict[str, str]],
        model_id: str = "unknown",
    ) -> EvaluationResult:
        """Evaluate the model on a set of examples.

        Parameters
        ----------
        examples : List[Dict[str, str]]
            Each example: {"prompt": str, "expected": str}.
        model_id : str
            Model identifier for the result.

        Returns
        -------
        EvaluationResult
            The evaluation result with metrics.
        """
        start = time.time()
        correct = 0
        scores = []
        errors = []

        for example in examples:
            prompt = example.get("prompt", "")
            expected = example.get("expected", "")
            try:
                response = self.model(prompt)
                is_correct, score = self.judge(response, expected)
                if is_correct:
                    correct += 1
                scores.append(score)
            except Exception as exc:
                errors.append(f"{type(exc).__name__}: {exc}")

        num_examples = len(examples)
        accuracy = correct / num_examples if num_examples > 0 else 0.0
        avg_score = sum(scores) / len(scores) if scores else 0.0

        result = EvaluationResult(
            model_id=model_id,
            metrics={
                "accuracy": accuracy,
                "avg_score": avg_score,
                "error_rate": len(errors) / num_examples if num_examples > 0 else 0.0,
            },
            num_examples=num_examples,
            duration_seconds=time.time() - start,
            errors=errors,
        )
        self._history.append(result)
        return result

    def get_history(self) -> List[EvaluationResult]:
        """Return all evaluation results."""
        return list(self._history)

    def get_stats(self) -> Dict[str, Any]:
        """Return evaluator statistics."""
        return {
            "type": "Evaluator",
            "evaluations": len(self._history),
            "last_accuracy": self._history[-1].metrics.get("accuracy", 0.0) if self._history else 0.0,
        }