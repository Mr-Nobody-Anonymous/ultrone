# Copyright (c) Ultrone Contributors. All rights reserved.
"""Evolutionary search over architecture genomes + the lab entry point.

Each generation: breed bounded mutations from the current elite pool,
measure every child with real sandbox micro-benchmarks, gate promotions,
update niche archives, and let the experiment designer attack the worst
weakness of the current canonical candidate.

Everything is deterministic under ``seed``; every number in the returned
:class:`LabReport` is reproducible.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from self_improvement.lab.analyst import ResearchAnalyst, capability_trajectory
from self_improvement.lab.candidate_manager import (
    CandidateRegistry,
    EliteArchive,
)
from self_improvement.lab.evaluator import CapabilitySnapshot, measure_genome
from self_improvement.lab.experiment_designer import (
    design_next_experiment,
    detect_weaknesses,
    run_experiment,
)
from self_improvement.lab.genome import Genome, make_genome, mutate, seed_population


@dataclass
class LabReport:
    timeline: List[Dict[str, Any]]          # per-generation best summaries
    promotions: List[str]
    archive: Dict[str, str]                 # niche -> candidate_id
    designer_log: List[Dict[str, Any]]
    registry_size: int
    analyses: List[Any] = field(default_factory=list)   # AnalysisReport per gen
    trajectory: Optional[Dict[str, Any]] = None         # plot-ready series


def _best(pop: List[CapabilitySnapshot]) -> CapabilitySnapshot:
    return max(pop, key=lambda s: (s.capability_index, s.candidate_id))


def run_lab(
    seed: int = 0,
    generations: int = 3,
    pop_size: int = 4,
    audit_store=None,
) -> LabReport:
    rng = random.Random(seed ^ 0x51AB1)
    registry = CandidateRegistry()
    archive = EliteArchive()
    designer_log: List[Dict[str, Any]] = []
    promotions: List[str] = []
    timeline: List[Dict[str, Any]] = []
    analyst = ResearchAnalyst()
    analyses: List[Any] = []

    # Generation 0: spread-out founders.
    population = [
        measure_genome(g, seed=seed) for g in seed_population(rng, pop_size, 0)
    ]
    for snap in population:
        registry.register(snap)
        archive.consider(snap)

    canonical = _best(population)
    registry.promote(canonical.candidate_id, audit_store=audit_store)
    promotions.append(canonical.candidate_id)
    timeline.append(canonical.summary())

    for generation in range(1, generations + 1):
        elites = sorted(
            population, key=lambda s: (-s.capability_index, s.candidate_id),
        )[: max(2, pop_size // 2)]

        children: List[CapabilitySnapshot] = []
        for elite in elites:
            child_genome = mutate(
                _genome_of(elite, registry), rng, generation,
            )
            child = measure_genome(child_genome, seed=seed)
            registry.register(child)
            archive.consider(child)
            children.append(child)

            # One designed experiment against the current canonical's
            # biggest weakness, using this child as the base.
            proposal = design_next_experiment(canonical)
            if proposal is not None:
                evidence = run_experiment(proposal, child_genome, seed=seed)
                designer_log.append({
                    "generation": generation,
                    "hypothesis": proposal.hypothesis,
                    "target_dim": proposal.target_dim,
                    "confirmed": evidence.confirmed,
                    "delta": evidence.delta,
                })
                if evidence.confirmed:
                    improved = evidence.child_snapshot
                    try:
                        registry.register(improved)
                    except ValueError:
                        pass  # already known: append-only, never overwritten
                    archive.consider(improved)

        population = elites + children
        best = _best(population)
        if best.candidate_id != canonical.candidate_id:
            gate = registry.promote(best.candidate_id, audit_store=audit_store)
            if gate.passed and registry.canonical_id == best.candidate_id:
                canonical = registry.get(best.candidate_id).snapshot
                promotions.append(canonical.candidate_id)
        timeline.append(canonical.summary())
        analyst = analyst.observe(canonical)
        report_analysis = analyst.compare()
        if report_analysis is not None:
            analyses.append(report_analysis)

    return LabReport(
        timeline=timeline,
        promotions=promotions,
        archive={n: s.candidate_id for n, s in archive.leaders.items()},
        designer_log=designer_log,
        registry_size=len(registry),
        analyses=analyses,
        trajectory=capability_trajectory(analyst.history),
    )


def _genome_of(snapshot: CapabilitySnapshot,
               registry: Optional[CandidateRegistry] = None) -> Genome:
    """Reconstruct a Genome from a snapshot's recorded architecture."""
    arch = snapshot.architecture
    return make_genome(
        parameter_count=int(arch["parameter_count"]),
        memory_capacity=int(arch["memory_capacity"]),
        planning_depth=int(arch["planning_depth"]),
        tool_policy=str(arch["tool_policy"]),
        noise_floor=float(arch["noise_floor"]),
        generation=snapshot.generation,
        parents=(snapshot.parent_id,) if snapshot.parent_id else (),
    )
