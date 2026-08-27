# Copyright (c) Ultrone Contributors. All rights reserved.
"""Ordered fallback across routing candidates.

Selection ranks candidates; fallback is what happens when reality
disagrees with the ranking. The first candidate that validates wins;
each failure drops that candidate from the queue and the next attempt
is priced *cumulatively* -- resilience is not free, which is exactly
the pressure that teaches the optimizer to stop under-provisioning
cheap primary routes on demanding tasks.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Generic, Iterable, List, Optional, TypeVar

T = TypeVar("T")


@dataclass
class FallbackChain(Generic[T]):
    """Deterministic candidate queue with tried-candidate removal."""

    candidates: List[Any] = field(default_factory=list)   # list[(obj,key)]
    max_attempts: int = 3

    def __post_init__(self) -> None:
        if self.max_attempts < 1:
            raise ValueError("max_attempts must be >= 1")

    @property
    def exhausted(self) -> bool:
        return len(self.candidates) == 0

    @property
    def attempts_left(self) -> int:
        return min(self.max_attempts, len(self.candidates))

    def next_candidate(self) -> Optional[Any]:
        """Pop-and-return the current best untried candidate."""
        if not self.candidates:
            return None
        _, obj = self.candidates.pop(0)
        return obj

    def record_failure(self) -> None:
        """Bookkeeping hook; the pop in ``next_candidate`` already
        removed the failed candidate."""

    def remaining_keys(self) -> List[str]:
        return [key for key, _ in self.candidates]


def build_chain(ranked: Iterable[tuple],
                max_attempts: int = 3) -> FallbackChain:
    """Wrap ranked ``(sort_key, obj)`` pairs into a FallbackChain.

    Assumes ``ranked`` arrives best-first (the router guarantees it);
    keys ride along for introspection in traces.
    """
    return FallbackChain(candidates=list(ranked),
                         max_attempts=max_attempts)