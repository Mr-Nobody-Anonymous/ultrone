# Copyright (c) Ultrone Contributors. All rights reserved.
"""Frontier Reasoning — base protocols and abstractions.

Defines the pluggable interfaces that drive all frontier reasoning strategies:

- ``Solver``: produces a solution/answer from a prompt (an LLM, a model, or a
  test double). This is the *only* backend dependency; every strategy in this
  package accepts a ``Solver`` and thus works with any provider.
- ``Verifier``: scores / checks a solution. Used by self-consistency,
  self-correction, constitutional critique, and the benchmark harness.
- ``ReasoningStrategy``: the common interface all strategies implement.

The design follows the project's composition-over-inheritance principle: a
strategy wraps one or more ``Solver`` instances and/or ``Verifier`` instances
rather than subclassing concrete providers.
"""

from __future__ import annotations

import abc
import logging
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Protocol, Sequence

logger = logging.getLogger("Ultrone.Frontier.Reasoning")


class Solver(Protocol):
    """A callable that produces a solution string from a prompt."""

    def __call__(self, prompt: str, **kwargs: Any) -> str:
        """Return a solution for ``prompt``.

        Implementations may be LLM-backed, rule-based, or test doubles.
        ``kwargs`` may carry sampling temperature, max tokens, etc.
        """
        ...


class Verifier(Protocol):
    """A callable that evaluates a solution."""

    def __call__(self, solution: str, prompt: str, **kwargs: Any) -> "Verification":
        """Return a :class:`Verification` for ``solution`` against ``prompt``."""
        ...


@dataclass
class Verification:
    """The outcome of verifying a solution."""

    passes: bool
    score: float = 0.0
    feedback: str = ""
    details: Dict[str, Any] = field(default_factory=dict)

    def __bool__(self) -> bool:
        return self.passes


@dataclass
class ReasoningTrace:
    """A structured, auditable record of a reasoning run.

    Every strategy records a trace so the self-improvement loop and benchmark
    harness can analyze where reasoning succeeds or fails.
    """

    strategy: str = ""
    prompt: str = ""
    solution: str = ""
    confidence: float = 0.0
    steps: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "strategy": self.strategy,
            "prompt": self.prompt,
            "solution": self.solution,
            "confidence": self.confidence,
            "steps": self.steps,
            "metadata": self.metadata,
        }


@dataclass
class ReasoningResult:
    """The final output of a reasoning strategy."""

    solution: str
    confidence: float = 0.0
    trace: Optional[ReasoningTrace] = None
    candidates: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "solution": self.solution,
            "confidence": self.confidence,
            "trace": self.trace.to_dict() if self.trace else None,
            "metadata": self.metadata,
        }


class ReasoningStrategy(abc.ABC):
    """Abstract base class for all frontier reasoning strategies.

    Subclasses implement :meth:`strategy_name` and :meth:`solve` and inherit
    the tracing bookkeeping from :meth:`solve_with_trace`.
    """

    def __init__(self, solver: Optional[Solver] = None, **config: Any) -> None:
        self.solver = solver
        self.config: Dict[str, Any] = dict(config)
        self._history: List[ReasoningTrace] = []

    @abc.abstractmethod
    def strategy_name(self) -> str:
        """Return the human-readable strategy name."""

    @abc.abstractmethod
    def solve(self, prompt: str, **kwargs: Any) -> ReasoningResult:
        """Apply the strategy to ``prompt`` and return a result."""

    def solve_with_trace(self, prompt: str, **kwargs: Any) -> ReasoningResult:
        """Run :meth:`solve` and record an auditable trace."""
        result = self.solve(prompt, **kwargs)
        trace = ReasoningTrace(
            strategy=self.strategy_name(),
            prompt=prompt,
            solution=result.solution,
            confidence=result.confidence,
            steps=list(result.trace.steps) if result.trace else [],
            metadata=result.metadata,
        )
        result.trace = trace
        self._history.append(trace)
        return result

    def get_history(self) -> List[ReasoningTrace]:
        """Return all recorded traces."""
        return list(self._history)

    def get_stats(self) -> Dict[str, Any]:
        """Return aggregate statistics for this strategy instance."""
        return {
            "strategy": self.strategy_name(),
            "runs": len(self._history),
            "avg_confidence": (
                sum(t.confidence for t in self._history) / len(self._history)
                if self._history
                else 0.0
            ),
        }


def _argmax(collection: Sequence[Any], key: Callable[[Any], float]) -> int:
    """Return the index of the maximum element by ``key``."""
    if not collection:
        return -1
    best_idx = 0
    best_val = key(collection[0])
    for idx, item in enumerate(collection[1:], start=1):
        val = key(item)
        if val > best_val:
            best_val = val
            best_idx = idx
    return best_idx
