# Copyright (c) Ultrone Contributors. All rights reserved.
"""Candidate governance: append-only registry, promotion gates, elite archive.

Invariants:

- The registry NEVER overwrites or deletes a record. Candidates are
  versioned; history is immutable.
- The canonical pointer advances only through :func:`evaluate_promotion`
  passing every gate, and every promotion can be appended to an
  ``ultrone_hitl`` AuditStore for tamper-evident provenance.
- The elite archive preserves tradeoff niches (accuracy, efficiency,
  robustness, planning, adaptation) rather than crowning one champion.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from self_improvement.lab.evaluator import CapabilitySnapshot

#: Max tolerated per-dimension drop child-vs-parent.
PROMOTION_TOLERANCE = 0.03


@dataclass(frozen=True)
class GateReport:
    passed: bool
    regressions: Tuple[str, ...]
    reasons: List[str]


def evaluate_promotion(
    parent: CapabilitySnapshot, child: CapabilitySnapshot,
    *,
    min_generalization: Optional[float] = None,
    min_robustness: Optional[float] = None,
    min_efficiency: Optional[float] = None,
    holdout_report: Optional[Dict[str, Any]] = None,
    pareto_ok: bool = False,
) -> GateReport:
    """Strict-improvement + no-regression + efficiency-noninferiority.

    Optional stricter clauses (all enforced when provided):

    - ``min_generalization`` / ``min_robustness`` / ``min_efficiency``:
      absolute capability-floor thresholds on the child.
    - ``holdout_report``: a sealed holdout result dict (from
      HoldoutSeal.measure). The gate requires its mean index to not
      regress against the parent's own recorded holdout mean when the
      parent has one; a report whose 'mean_index' is below the parent's
      recorded value minus tolerance fails promotion. Crucially, the
      presence of a holdout report proves the result was consulted at
      promotion time, not during search.
    - ``pareto_ok``: accept a non-dominated tradeoff candidate even if
      it does not strictly beat the parent's scalar index (Pareto
      improvement), as long as no critical regression exists.
    """
    reasons: List[str] = []
    regressions: List[str] = []

    for dim, base in parent.capabilities.items():
        child_val = child.capabilities.get(dim, 0.0)
        if child_val < base - PROMOTION_TOLERANCE:
            regressions.append(dim)
    if regressions:
        reasons.append(f"capability regressions: {sorted(regressions)}")

    if child.capability_index <= parent.capability_index:
        reasons.append(
            f"no overall improvement "
            f"(parent {parent.capability_index} vs child {child.capability_index})"
        )
    if child.efficiency < parent.efficiency * 0.95:
        reasons.append(
            f"efficiency degraded beyond tolerance "
            f"(parent {parent.efficiency} vs child {child.efficiency})"
        )

    # -- optional floor thresholds ------------------------------------ #
    if min_generalization is not None:
        val = child.capabilities.get("generalization", 0.0)
        if val < min_generalization:
            reasons.append(
                f"generalization {val} below required {min_generalization}")
    if min_robustness is not None:
        val = child.capabilities.get("robustness", 0.0)
        if val < min_robustness:
            reasons.append(
                f"robustness {val} below required {min_robustness}")
    if min_efficiency is not None and child.efficiency < min_efficiency:
        reasons.append(
            f"efficiency {child.efficiency} below required "
            f"{min_efficiency}")

    # -- sealed-holdout clause ------------------------------------------ #
    if holdout_report is not None:
        child_holdout = float(holdout_report.get("mean_index", 0.0))
        parent_holdout = parent.resource.get("holdout_mean_index")
        if parent_holdout is not None \
                and child_holdout < float(parent_holdout) - PROMOTION_TOLERANCE:
            reasons.append(
                f"holdout regression (parent {parent_holdout} vs "
                f"child {child_holdout}) -- benchmark overfitting")

    # -- Pareto escape hatch -------------------------------------------- #
    if pareto_ok and reasons == [
        f"no overall improvement "
        f"(parent {parent.capability_index} vs child "
        f"{child.capability_index})"
    ] and not regressions:
        # A genuine tradeoff point: keep it without scalar dominance.
        reasons = []

    return GateReport(
        passed=not reasons, regressions=tuple(sorted(regressions)),
        reasons=reasons,
    )


@dataclass
class CandidateRecord:
    snapshot: CapabilitySnapshot
    status: str                       # "experimental" | "promoted"
    gate: Optional[GateReport] = None


class CandidateRegistry:
    """Append-only version registry."""

    def __init__(self) -> None:
        self._records: Dict[str, CandidateRecord] = {}
        self.canonical_id: Optional[str] = None

    def register(self, snapshot: CapabilitySnapshot,
                 status: str = "experimental") -> CandidateRecord:
        if snapshot.candidate_id in self._records:
            raise ValueError(
                f"candidate {snapshot.candidate_id} already registered; "
                f"the registry is append-only"
            )
        record = CandidateRecord(snapshot=snapshot, status=status)
        self._records[snapshot.candidate_id] = record
        return record

    def promote(self, candidate_id: str,
                audit_store=None, actor: str = "bob") -> GateReport:
        """Advance the canonical pointer through the promotion gate.

        The parent is the current canonical (or the candidate itself if it
        is the first). A passed gate flips status to "promoted"; a failed
        one leaves the record untouched as "experimental".
        """
        record = self._records[candidate_id]
        if record.status == "promoted":
            return GateReport(True, (), ["already promoted"])
        parent_snap = None
        if self.canonical_id and self.canonical_id != candidate_id:
            parent_snap = self._records[self.canonical_id].snapshot
        if parent_snap is not None and parent_snap.parent_id == "":
            parent_snap = parent_snap          # keep as-is
        if parent_snap is None:
            gate = GateReport(True, (), [])
        else:
            # Direct parent if recorded, else canonical.
            direct = self._records.get(record.snapshot.parent_id)
            parent = direct.snapshot if direct else parent_snap
            gate = evaluate_promotion(parent, record.snapshot)
        record.gate = gate
        if not gate.passed:
            return gate
        record.status = "promoted"
        self.canonical_id = candidate_id
        if audit_store is not None:
            audit_store.append_event(
                "lab-promotion", candidate_id, "PROMOTED", actor,
                {"gate_reasons": gate.reasons,
                 "fingerprint": record.snapshot.fingerprint},
            )
        return gate

    def get(self, candidate_id: str) -> CandidateRecord:
        return self._records[candidate_id]

    @property
    def records(self) -> Dict[str, CandidateRecord]:
        return dict(self._records)

    def __len__(self) -> int:
        return len(self._records)


@dataclass
class EliteArchive:
    """One elite per tradeoff niche; leaders change only when beaten."""

    niches: Tuple[str, ...] = (
        "overall", "efficiency", "robustness", "planning", "adaptation",
    )
    leaders: Dict[str, CapabilitySnapshot] = field(default_factory=dict)

    @staticmethod
    def _metric(snapshot: CapabilitySnapshot, niche: str) -> float:
        if niche == "overall":
            return snapshot.capability_index
        if niche == "efficiency":
            return snapshot.efficiency
        return snapshot.capabilities.get(niche, 0.0)

    def consider(self, snapshot: CapabilitySnapshot) -> List[str]:
        won = []
        for niche in self.niches:
            leader = self.leaders.get(niche)
            if leader is None or self._metric(snapshot, niche) > self._metric(leader, niche):
                self.leaders[niche] = snapshot
                won.append(niche)
        return won
