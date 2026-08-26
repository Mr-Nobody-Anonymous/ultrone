# Copyright (c) Ultrone Contributors. All rights reserved.
"""Research Analyst: self-analysis of evaluation history.

The scientific loop is:

    analysis -> hypothesis -> experiment -> evidence

NOT:

    analysis -> arbitrary self-modification.

The analyst inspects the *history* of CapabilitySnapshots (the lab's
timeline and designer log) and produces structured findings: per-
dimension deltas across generations, coupling diagnoses (one dimension
improving while another regresses suggests a shared resource), and a
recommended next experiment. It never modifies anything -- its output
is a recommendation that feeds back into ``experiment_designer``.

It also produces the capability trajectory: the plot-ready series that
turns "ULTRONE is getting smarter" into an empirical statement.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence

from self_improvement.lab.evaluator import CapabilitySnapshot


@dataclass(frozen=True)
class DimensionDelta:
    """Change in one capability dimension across a generation step."""

    dimension: str
    before: float
    after: float
    delta: float                       # after - before, signed

    @property
    def direction(self) -> str:
        if self.delta > 1e-6:
            return "improved"
        if self.delta < -1e-6:
            return "regressed"
        return "flat"


@dataclass(frozen=True)
class Diagnosis:
    """A cross-dimension finding from comparing consecutive snapshots."""

    kind: str                          # "coupling" | "tradeoff" | "plateau"
    dimensions: tuple                  # involved dimensions
    statement: str                     # human-readable finding
    confidence: float                  # 0..1, transparent formula


@dataclass(frozen=True)
class AnalysisReport:
    """What the analyst observed -- evidence, never direct action."""

    from_candidate: str
    to_candidate: str
    deltas: List[DimensionDelta]
    diagnoses: List[Diagnosis]
    recommended_change: Optional[Dict[str, Any]]   # for the designer
    rationale: str = ""

    @property
    def headline(self) -> str:
        ups = [d.dimension for d in self.deltas if d.direction == "improved"]
        downs = [d.dimension for d in self.deltas if d.direction == "regressed"]
        parts = []
        if ups:
            parts.append(f"improved: {', '.join(ups)}")
        if downs:
            parts.append(f"regressed: {', '.join(downs)}")
        return "; ".join(parts) or "no measurable change"


#: Coupling rules: if A improves while B regresses beyond tolerance,
#: hypothesize a shared-resource cause. Keys are (up, down) pairs.
_COUPLING_RULES: Dict[tuple, Dict[str, Any]] = {
    ("reasoning", "memory"): {
        "statement": "new reasoning module increases context consumption "
                     "and causes memory retrieval degradation",
        "recommended_change": {"memory_capacity": "+16"},
    },
    ("planning", "prediction"): {
        "statement": "deeper planning extends horizon assumptions that "
                     "the belief model cannot track",
        "recommended_change": {"noise_floor": "x0.75"},
    },
    ("tool_use", "robustness"): {
        "statement": "longer tool chains add failure surfaces under shift",
        "recommended_change": {"tool_policy": "greedy"},
    },
}


@dataclass(frozen=True)
class ResearchAnalyst:
    """Stateless analyzer over snapshot history; immutable per observation."""

    regression_tolerance: float = 0.02
    plateau_epsilon: float = 1e-4
    history: List[CapabilitySnapshot] = field(default_factory=list)

    def observe(self, snapshot: CapabilitySnapshot) -> "ResearchAnalyst":
        """Return an analyst whose includes this snapshot."""
        return ResearchAnalyst(
            regression_tolerance=self.regression_tolerance,
            plateau_epsilon=self.plateau_epsilon,
            history=[*self.history, snapshot],
        )

    # -- analysis --------------------------------------------------------- #
    def compare(self) -> Optional[AnalysisReport]:
        """Analyze the last two snapshots in history, if there are two."""
        if len(self.history) < 2:
            return None
        before, after = self.history[-2], self.history[-1]
        deltas = [
            DimensionDelta(
                dimension=dim,
                before=before.capabilities.get(dim, 0.0),
                after=after.capabilities.get(dim, 0.0),
                delta=round(after.capabilities.get(dim, 0.0)
                            - before.capabilities.get(dim, 0.0), 4),
            )
            for dim in sorted(before.capabilities)
        ]
        diagnoses = self._diagnose(deltas)

        recommended: Optional[Dict[str, Any]] = None
        rationale_parts: List[str] = []
        for diag in diagnoses:
            if diag.kind == "coupling":
                rule = _COUPLING_RULES.get(diag.dimensions)
                if rule:
                    recommended = dict(rule["recommended_change"])
                    rationale_parts.append(rule["statement"])
                    break

        return AnalysisReport(
            from_candidate=before.candidate_id,
            to_candidate=after.candidate_id,
            deltas=deltas,
            diagnoses=diagnoses,
            recommended_change=recommended,
            rationale="; ".join(rationale_parts),
        )

    def _diagnose(self, deltas: Sequence[DimensionDelta]) -> List[Diagnosis]:
        tol = self.regression_tolerance
        eps = self.plateau_epsilon
        ups = [d for d in deltas if d.delta > eps]
        downs = [d for d in deltas if d.delta < -tol]
        out: List[Diagnosis] = []

        # 1) Cross-dimension couplings (checked first; most informative).
        matched_pairs = set()
        for up in sorted(ups, key=lambda d: -d.delta):
            for down in sorted(downs, key=lambda d: d.delta):
                pair = (up.dimension, down.dimension)
                rule = _COUPLING_RULES.get(pair)
                if rule:
                    matched_pairs.add(pair)
                    out.append(Diagnosis(
                        kind="coupling",
                        dimensions=pair,
                        statement=rule["statement"],
                        confidence=round(min(1.0, abs(up.delta)
                                             + abs(down.delta)), 3),
                    ))
                    break

        # 2) Plain tradeoffs: any remaining improvement/regression pair.
        for up in sorted(ups, key=lambda d: -d.delta):
            for down in sorted(downs, key=lambda d: d.delta):
                pair = (up.dimension, down.dimension)
                if pair in matched_pairs:
                    continue
                matched_pairs.add(pair)
                out.append(Diagnosis(
                    kind="tradeoff",
                    dimensions=pair,
                    statement=(
                        f"{up.dimension} +{up.delta:.3f} came at the cost "
                        f"of {down.dimension} {down.delta:.3f}"),
                    confidence=round(
                        min(1.0, abs(up.delta) / max(abs(down.delta), 1e-9))
                        * 0.5, 3),
                ))

        # 3) Plateau: nothing moved meaningfully.
        if not ups and not downs:
            out.append(Diagnosis(
                kind="plateau",
                dimensions=tuple(),
                statement="no dimension moved beyond epsilon; the current "
                          "knobs are exhausted -- mutate more aggressively",
                confidence=0.9,
            ))
        return out


# --------------------------------------------------------------------- #
# Novelty: did evolution find a genuinely different solution?            #
# --------------------------------------------------------------------- #
@dataclass(frozen=True)
class NoveltyAssessment:
    """Three orthogonal distances between a child and its parent.

    - architectural -- normalized L1 distance over genome knobs
      (did the *design* change?);
    - behavioral    -- L2 distance over capability vectors (does it
      *behave* differently?);
    - performance   -- signed capability-index delta (did it get
      better on the measured objectives?).

    Labels:

    - ``refinement``  -- small design change, small behavior change;
    - ``pivot``       -- large design change with comparable or better
      performance: a genuinely different solution strategy;
    - ``tuning``      -- tiny design change, meaningful gain: the same
      strategy pushed harder;
    - ``regression``  -- performance fell.
    """

    parent_id: str
    child_id: str
    architectural_distance: float          # 0..1, knob-space L1 / range
    behavioral_distance: float             # 0..sqrt(n), capability L2
    performance_delta: float               # signed index delta
    label: str

def assess_novelty(
    parent: CapabilitySnapshot,
    child: CapabilitySnapshot,
    parent_knobs: Optional[Dict[str, Any]] = None,
    child_knobs: Optional[Dict[str, Any]] = None,
) -> NoveltyAssessment:
    """Classify whether the candidate is new wine or old wine."""
    from self_improvement.lab.genome import KNOB_BOUNDS
    arch_d = 0.0
    if parent_knobs and child_knobs:
        total, span = 0.0, 0.0
        for key, (lo, hi) in KNOB_BOUNDS.items():
            width = max(1e-9, float(hi) - float(lo))
            pv = float(parent_knobs.get(key, lo))
            cv = float(child_knobs.get(key, lo))
            if isinstance(pv, str) or isinstance(cv, str):
                total += 0.0 if str(pv) == str(cv) else 1.0
                span += 1.0
            else:
                total += abs(cv - pv) / width
                span += 1.0
        arch_d = round(min(1.0, total / span), 4)

    common = sorted(set(parent.capabilities) & set(child.capabilities))
    behav_d = round(
        math.sqrt(sum((child.capabilities[d] - parent.capabilities[d]) ** 2
                      for d in common)), 4) if common else 0.0
    perf_d = round(child.capability_index - parent.capability_index, 6)

    if perf_d < -1e-4:
        label = "regression"
    elif arch_d >= 0.3 and perf_d >= -1e-4:
        label = "pivot"
    elif arch_d < 0.05 and perf_d > 0.01:
        label = "tuning"
    else:
        label = "refinement"
    return NoveltyAssessment(
        parent_id=parent.candidate_id,
        child_id=child.candidate_id,
        architectural_distance=arch_d,
        behavioral_distance=behav_d,
        performance_delta=perf_d,
        label=label,
    )


def analyze_history(history: List[CapabilitySnapshot]
                    ) -> Optional[AnalysisReport]:
    """Convenience wrapper: analyze the final transition of a history."""
    analyst = ResearchAnalyst()
    for snap in history:
        analyst = analyst.observe(snap)
    return analyst.compare()


def capability_trajectory(history: Sequence[CapabilitySnapshot]
                          ) -> Dict[str, Any]:
    """Plot-ready series: 'is ULTRONE getting smarter' as empirical data."""
    if not history:
        return {"candidates": [], "generations": [], "capability_index": [],
                "efficiency": [], "dimensions": {}}
    dims = sorted(history[0].capabilities)
    return {
        "candidates": [s.candidate_id for s in history],
        "generations": [s.generation for s in history],
        "capability_index": [s.capability_index for s in history],
        "efficiency": [s.efficiency for s in history],
        "dimensions": {
            dim: [round(s.capabilities.get(dim, 0.0), 4) for s in history]
            for dim in dims
        },
    }
