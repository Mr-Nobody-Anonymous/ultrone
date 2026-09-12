# Copyright (c) Ultrone Contributors. All rights reserved.
"""Governed promotion of a trained candidate into production.

The gap between *the model is better in training* and *the model is
production* is the gate. This module reuses the existing adaptive
stack -- ``adaptive.evaluator.Evaluator`` (reproducibility + margin
gates), ``adaptive.promotion.PromotionGate`` (audited record) and
``adaptive.promotion.BrainStore`` (versioned channels) -- and points
them at a LearnedWeights candidate over a deterministic holdout
family.

A candidate reaches production only when BOTH pass:

1. the Evaluator gate (bare margin over baseline, reproducible); and
2. the regression suite (bounded aggression -- no family broken).

Any rejection is recorded in the gate's immutable history before a
single production byte is touched.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from adaptive.optimizer import config_hash
from adaptive.promotion import BrainStore, PromotionGate

from self_improvement.self_training.regression import (
    RegressionReport,
    score_weights,
)
from self_improvement.self_training.trainer import LearnedWeights


@dataclass
class PromotionDecision:
    decision: str             # promote | reject | non_reproducible
    reason: str
    candidate_score: float
    baseline_score: float
    margin_required: float
    candidate_hash: str
    baseline_hash: str
    regression_passed: bool
    record_id: Optional[int] = None   # PromotionGate record when reviewed

    @property
    def promoted(self) -> bool:
        return self.decision == "promote"


def _objective(holdout: List[Any]) -> Any:
    """Deterministic per-config score over a fixed holdout family."""
    def task(config: Dict[str, Any]) -> float:
        weights = LearnedWeights.from_config(config)
        scores = score_weights(weights, holdout)
        return (sum(scores.values()) / len(scores) if scores else 0.0)
    return task


def make_promoter(holdout: List[Any], *,
                  margin: float = 0.01,
                  repeats: int = 3) -> "Promoter":
    """Build a governed promoter pinned to a holdout family."""
    return Promoter(holdout=holdout, margin=margin, repeats=repeats)


class Promoter:
    """Evaluator gate + gate record + BrainStore write, in order."""

    def __init__(self, holdout: List[Any], *,
                 margin: float = 0.01,
                 repeats: int = 3,
                 brain: Optional[BrainStore] = None) -> None:
        from adaptive.evaluator import Evaluator
        if repeats < 2:
            raise ValueError("repeats must be >= 2 for reproducibility")
        self._holdout = list(holdout)
        self._evaluator = Evaluator(task=_objective(self._holdout),
                                    margin=margin, repeats=repeats)
        self._gate = PromotionGate()
        self._store = brain

    # -- the gate -------------------------------------------------------- #
    def run(self, candidate: LearnedWeights,
            baseline: LearnedWeights,
            regression: Optional[RegressionReport] = None,
            *, persist: bool = True) -> PromotionDecision:
        cand_cfg = candidate.to_config()
        base_cfg = baseline.to_config()
        result = self._evaluator.evaluate(cand_cfg, base_cfg)
        regression_passed = regression.passed if regression else True

        candidate_score = result.candidate_score
        baseline_score = result.baseline_score
        reason_parts = [result.reason]
        final_result = result
        if not regression_passed:
            from adaptive.evaluator import EvaluationResult
            final_result = EvaluationResult(
                decision="reject",
                candidate_score=result.candidate_score,
                baseline_score=result.baseline_score,
                margin_required=result.margin_required,
                repeats=result.repeats,
                reason=(f"{result.reason}; regression failures in: "
                        f"{', '.join(regression.family_regressions)}"))

        # The gate records the HONEST verdict -- if regression failed,
        # the audited record says 'reject', never 'promote'.
        record = self._gate.review(final_result, cand_cfg,
                                   config_hash(cand_cfg))
        review_decision = final_result.decision
        reason = final_result.reason

        if review_decision == "promote" and persist \
                and self._store is not None:
            self._store.set_config("baseline", base_cfg)
            self._store.promote(cand_cfg, record, self._gate)

        return PromotionDecision(
            decision=review_decision,
            reason=reason,
            candidate_score=candidate_score,
            baseline_score=baseline_score,
            margin_required=result.margin_required,
            candidate_hash=config_hash(cand_cfg),
            baseline_hash=config_hash(base_cfg),
            regression_passed=regression_passed,
            record_id=record.record_id)

    @property
    def history(self):
        return self._gate.history