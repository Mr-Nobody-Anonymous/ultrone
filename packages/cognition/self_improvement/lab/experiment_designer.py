# Copyright (c) Ultrone Contributors. All rights reserved.
"""Experiment designer: weakness -> hypothesis -> ranked experiment.

The scientific loop, not arbitrary self-modification:

    analysis (CapabilitySnapshot deltas)
        -> hypothesis (from a transparent rule library)
        -> ranked by expected information gain vs cost
        -> one experiment selected
        -> sandbox evaluation
        -> evidence (confirmed / refuted)
        -> knowledge update

The designer proposes CHANGES TO CANDIDATE CONFIGURATIONS; it can never
modify the canonical system or the code base.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any, Dict, List, Optional, Tuple

from self_improvement.lab.evaluator import CapabilitySnapshot
from self_improvement.lab.genome import Genome, make_genome

#: Capability target used to compute deficits for standalone snapshots.
DEFICIT_TARGET = 0.75

#: Cost per experiment (flat penalty in the information-gain ranking).
EXPERIMENT_COST = 0.10


@dataclass(frozen=True)
class Weakness:
    dimension: str
    score: float
    gap: float


@dataclass(frozen=True)
class ExperimentProposal:
    hypothesis: str
    target_dim: str
    change: Dict[str, Any]
    rationale: str
    info_gain: float


@dataclass(frozen=True)
class Evidence:
    proposal: ExperimentProposal
    child_snapshot: CapabilitySnapshot
    delta: float                    # change on the targeted dimension
    confirmed: bool


def detect_weaknesses(
    snapshot: CapabilitySnapshot, baseline: Optional[CapabilitySnapshot] = None,
) -> List[Weakness]:
    """Dimensions furthest below target (or below baseline), best-first."""
    out: List[Weakness] = []
    for dim, score in sorted(snapshot.capabilities.items()):
        if baseline is not None and dim in baseline.capabilities:
            gap = max(0.0, baseline.capabilities[dim] - score)
        else:
            gap = max(0.0, DEFICIT_TARGET - score)
        out.append(Weakness(dim, score, round(gap, 4)))
    return sorted(out, key=lambda w: (-w.gap, w.dimension))


#: Transparent hypothesis library: weakness dimension -> candidate changes.
HYPOTHESIS_LIBRARY: Dict[str, List[Dict[str, Any]]] = {
    "planning": [{
        "change": {"planning_depth": "+2"},
        "rationale": "deeper backward chaining should solve longer goal chains",
        "expected_gain": 0.15,
    }],
    "memory": [
        {"change": {"memory_capacity": "+16"},
         "rationale": "more associate slots reduce capacity eviction",
         "expected_gain": 0.12},
        {"change": {"memory_capacity": "+8"},
         "rationale": "smaller memory expansion, lower cost",
         "expected_gain": 0.06},
    ],
    "prediction": [{
        "change": {"noise_floor": "x0.5"},
        "rationale": "a lower belief floor sharpens posterior updates",
        "expected_gain": 0.10,
    }],
    "tool_use": [{
        "change": {"tool_policy": "deep"},
        "rationale": "deep search reaches tool chains beyond length 2",
        "expected_gain": 0.5,
    }],
    "generalization": [{
        "change": {"memory_capacity": "+8", "planning_depth": "+1"},
        "rationale": "generalization composes planning+memory+adaptation",
        "expected_gain": 0.08,
    }],
}


def _apply_change(genome: Genome, change: Dict[str, Any]) -> Genome:
    knobs = genome.knobs()
    new = dict(knobs)
    for knob, op in change.items():
        if op == "deep" or op == "greedy":
            new[knob] = op
        elif isinstance(op, str) and op.startswith("+"):
            new[knob] = int(knobs[knob]) + int(op[1:])
        elif isinstance(op, str) and op.startswith("x"):
            new[knob] = float(knobs[knob]) * float(op[1:])
        else:
            new[knob] = op
    return make_genome(
        parameter_count=int(new["parameter_count"]),
        memory_capacity=int(new["memory_capacity"]),
        planning_depth=int(new["planning_depth"]),
        tool_policy=str(new["tool_policy"]),
        noise_floor=float(new["noise_floor"]),
        generation=genome.generation + 1,
        parents=(genome.genome_id,),
    )


def design_next_experiment(
    snapshot: CapabilitySnapshot,
    baseline: Optional[CapabilitySnapshot] = None,
) -> Optional[ExperimentProposal]:
    """Rank hypotheses by information gain; return the best (or None)."""
    weaknesses = detect_weaknesses(snapshot, baseline)
    candidates: List[Tuple[float, ExperimentProposal]] = []
    for weakness in weaknesses:
        if weakness.gap <= 0.0:
            continue    # no deficit: experimenting here yields no information
        for h in HYPOTHESIS_LIBRARY.get(weakness.dimension, ()):
            gain = round(
                weakness.gap * (0.5 + h["expected_gain"]) - EXPERIMENT_COST, 4,
            )
            if gain <= 0.0:
                continue
            candidates.append((gain, ExperimentProposal(
                hypothesis=(
                    f"{h['change']} will improve '{weakness.dimension}' "
                    f"(now {weakness.score}) because {h['rationale']}"
                ),
                target_dim=weakness.dimension,
                change=h["change"],
                rationale=h["rationale"],
                info_gain=gain,
            )))
    if not candidates:
        return None
    candidates.sort(key=lambda t: (-t[0], t[1].target_dim, t[1].hypothesis))
    return candidates[0][1]


def run_experiment(
    proposal: ExperimentProposal, base_genome: Genome, seed: int = 0,
) -> Evidence:
    """Evaluate the proposed change in the sandbox; return evidence."""
    from self_improvement.lab.evaluator import measure_genome

    before = measure_genome(base_genome, seed=seed)
    child_genome = _apply_change(base_genome, proposal.change)
    after = measure_genome(child_genome, seed=seed)
    delta = round(
        after.capabilities.get(proposal.target_dim, 0.0)
        - before.capabilities.get(proposal.target_dim, 0.0), 6,
    )
    return Evidence(
        proposal=proposal, child_snapshot=after, delta=delta,
        confirmed=delta > 0.02,
    )
