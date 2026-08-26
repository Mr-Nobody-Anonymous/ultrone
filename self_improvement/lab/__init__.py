# Copyright (c) Ultrone Contributors. All rights reserved.
"""Controlled self-improvement laboratory (Sprint E).

Self-implementation as an *experimental loop*, never unrestricted
self-modification:

    analyze -> hypothesize -> experiment -> evidence -> gated promotion

Components:

- ``evaluator``           -- CapabilitySnapshot: a capability VECTOR (not a
                             single "smartness" number) measured by real
                             sandbox micro-benchmarks, plus efficiency
                             (capability / parameters) and regressions.
- ``candidate_manager``   -- append-only candidate registry, promotion
                             GATES, and an elite archive that preserves
                             tradeoff niches instead of one latest-best.
- ``evolutionary_search`` -- versioned architecture genomes (configurable
                             module graphs), bounded mutation, elitist
                             selection.
- ``experiment_designer`` -- weakness detection -> hypothesis -> ranked
                             experiments -> evidence -> knowledge update.

Hard invariants (tested):

1. The registry is append-only; the canonical pointer advances only
   through a passed gate, and every promotion is auditable.
2. Nothing here modifies the canonical system: candidates are versioned
   records evaluated inside the sandbox.
3. Everything is deterministic under (seed, configuration).
"""

from self_improvement.lab.analyst import (
    AnalysisReport,
    ResearchAnalyst,
    analyze_history,
    capability_trajectory,
)
from self_improvement.lab.candidate_manager import (
    EliteArchive,
    CandidateRegistry,
    GateReport,
    evaluate_promotion,
)
from self_improvement.lab.evaluator import CapabilitySnapshot, measure_genome
from self_improvement.lab.evolutionary_search import Genome, run_lab
from self_improvement.lab.experiment_designer import (
    design_next_experiment,
    detect_weaknesses,
    run_experiment,
)

__all__ = [
    "CapabilitySnapshot",
    "measure_genome",
    "CandidateRegistry",
    "GateReport",
    "evaluate_promotion",
    "EliteArchive",
    "Genome",
    "run_lab",
    "detect_weaknesses",
    "design_next_experiment",
    "run_experiment",
    "ResearchAnalyst",
    "AnalysisReport",
    "analyze_history",
    "capability_trajectory",
]
