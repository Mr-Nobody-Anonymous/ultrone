# Copyright (c) Ultrone Contributors. All rights reserved.
"""Structured-result validation: the benchmark decides, never hope.

A routed run ends in a :class:`StructuredResult`. Before its output
may count as delivered, the validator enforces the contract -- complete
payload, minimum confidence -- and the task's own demand bar (quality
must meet what task *difficulty* justifies). Failure is a normal,
first-class outcome: it routes the run into ``orchestration.fallback``
and is recorded verbatim in the trace.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict

from orchestration.task_classifier import TaskProfile


def _clamp01(value: float) -> float:
    return min(1.0, max(0.0, float(value)))


@dataclass(frozen=True)
class StructuredResult:
    """The only shape a backend may return through orchestration."""

    answer: Any
    quality: float                      # simulator-judged 0..1 fidelity
    model: str
    latency_ms: float
    artifacts: tuple = ()
    extras: Dict[str, Any] = None       # type: ignore[assignment]

    def __post_init__(self) -> None:
        if self.extras is None:
            object.__setattr__(self, "extras", {})

    @property
    def confidence(self) -> float:
        """Confidence proxy derived from measured quality.

        Kept a pure function of fidelity so tests and the optimizer can
        reason about acceptance analytically; real backends may supply
        calibrated confidence via ``extras`` later without changing the
        contract's consumers.
        """
        return round(0.55 + 0.40 * min(max(self.quality, 0.0), 1.0), 4)


@dataclass(frozen=True)
class ValidationReport:
    """Outcome of validating one structured result."""

    ok: bool
    reason: str
    quality: float
    confidence: float


#: Difficulty slope of the demand bar: quality owed grows with task
#: difficulty at this rate above the policy's intercept parameter.
DEMAND_SLOPE = 0.55


def demand_level(profile: TaskProfile,
                 intercept: float = 0.32) -> float:
    """Quality bar a difficulty-d profile is owed (clamped 0..1)."""
    return _clamp01(intercept + DEMAND_SLOPE * profile.difficulty)


def validate_result(result: StructuredResult,
                    profile: TaskProfile,
                    *,
                    demand_floor: float = 0.32,
                    min_confidence: float = 0.35) -> ValidationReport:
    """Apply the full acceptance contract to one result.

    Order matters for auditability: structural completeness first, then
    confidence floor, then the difficulty-derived demand bar. The first
    violated rule names itself in ``reason`` so traces read plainly.
    ``demand_floor`` acts as the zero-difficulty *intercept*; the slope
    (:data:`DEMAND_SLOPE`) is contract-level, not tunable per run --
    policies may decide how much to spend, not how little to owe.
    """
    if result.answer is None:
        return ValidationReport(
            ok=False, reason="missing answer payload",
            quality=result.quality, confidence=result.confidence)
    if not 0.0 <= result.quality <= 1.0:
        return ValidationReport(
            ok=False, reason="quality outside [0, 1]",
            quality=result.quality, confidence=result.confidence)
    if result.confidence < min_confidence:
        return ValidationReport(
            ok=False,
            reason=f"confidence {result.confidence} below floor "
                   f"{min_confidence}",
            quality=result.quality, confidence=result.confidence)

    # Task demand rises with difficulty: hard tasks owe harder answers.
    demand = demand_level(profile, intercept=demand_floor)
    if result.quality < demand:
        return ValidationReport(
            ok=False,
            reason=f"quality {result.quality:.4f} below demand "
                   f"{demand:.4f} (difficulty {profile.difficulty:.2f})",
            quality=result.quality, confidence=result.confidence)
    return ValidationReport(
        ok=True,
        reason=f"accepted at quality {result.quality:.4f}",
        quality=result.quality, confidence=result.confidence)