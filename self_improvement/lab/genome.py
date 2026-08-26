# Copyright (c) Ultrone Contributors. All rights reserved.
"""Versioned architecture genomes and bounded mutation.

A candidate ULTRONE is a *configuration*, not a blob: parameter budget,
memory capacity, planning depth, tool-search policy, and belief noise
floor. Every knob maps to a real sandbox micro-benchmark consequence
(see ``evaluator.py``), so evolution optimizes measured behavior.

Mutation is deliberately bounded -- evolution explores neighborhoods,
not arbitrary rewrites.
"""

from __future__ import annotations

import hashlib
import json
import random
from dataclasses import dataclass, replace
from typing import Dict

KNOB_BOUNDS = {
    "parameter_count": (100_000_000, 1_600_000_000),
    "memory_capacity": (4, 64),
    "planning_depth": (2, 8),
    "noise_floor": (0.005, 0.08),
}


@dataclass(frozen=True)
class Genome:
    genome_id: str
    generation: int
    parents: tuple
    parameter_count: int      # model-size budget for efficiency scoring
    memory_capacity: int      # slots in the continual-learning associate
    planning_depth: int       # max backward-chaining depth
    tool_policy: str          # "greedy" (chain <= 2) | "deep" (chain <= 4)
    noise_floor: float        # Bayesian belief floor (exploration of hypotheses)

    def knobs(self) -> Dict[str, object]:
        return {
            "parameter_count": self.parameter_count,
            "memory_capacity": self.memory_capacity,
            "planning_depth": self.planning_depth,
            "tool_policy": self.tool_policy,
            "noise_floor": self.noise_floor,
        }

    def stable_hash(self) -> str:
        payload = json.dumps(
            {"g": self.generation, **self.knobs()},
            sort_keys=True, separators=(",", ":"),
        )
        return hashlib.sha256(payload.encode()).hexdigest()[:12]


def make_genome(
    parameter_count: int, memory_capacity: int, planning_depth: int,
    tool_policy: str, noise_floor: float, generation: int = 0,
    parents: tuple = (),
) -> Genome:
    g = Genome(
        genome_id="", generation=generation, parents=tuple(parents),
        parameter_count=int(parameter_count),
        memory_capacity=int(memory_capacity),
        planning_depth=int(planning_depth),
        tool_policy=tool_policy,
        noise_floor=float(noise_floor),
    )
    return replace(g, genome_id=f"G{generation}-{g.stable_hash()}")


def seed_population(rng: random.Random, size: int, generation: int = 0):
    """Diverse, spread-out initial population."""
    pop = []
    lo_p, hi_p = KNOB_BOUNDS["parameter_count"]
    lo_m, hi_m = KNOB_BOUNDS["memory_capacity"]
    lo_d, hi_d = KNOB_BOUNDS["planning_depth"]
    lo_f, hi_f = KNOB_BOUNDS["noise_floor"]
    for i in range(size):
        frac = i / max(1, size - 1)
        pop.append(make_genome(
            parameter_count=int(lo_p + (hi_p - lo_p) * frac),
            memory_capacity=int(lo_m + (hi_m - lo_m) * frac),
            planning_depth=int(lo_d + (hi_d - lo_d) * frac),
            tool_policy="deep" if i % 2 == 0 else "greedy",
            noise_floor=lo_f * (hi_f / lo_f) ** frac,
            generation=generation,
        ))
    return pop


def mutate(genome: Genome, rng: random.Random, generation: int) -> Genome:
    """Apply 1-2 bounded knob changes. Returns a NEW immutable genome."""
    knobs = dict(genome.knobs())
    chosen = rng.sample(sorted(knobs), k=rng.choice((1, 2)))
    for knob in chosen:
        if knob == "parameter_count":
            lo, hi = KNOB_BOUNDS[knob]
            knobs[knob] = int(min(hi, max(lo, knobs[knob] * rng.choice((0.7, 1.4)))))
        elif knob == "memory_capacity":
            lo, hi = KNOB_BOUNDS[knob]
            knobs[knob] = int(min(hi, max(lo, knobs[knob] + rng.choice((-16, -8, 8, 16)))))
        elif knob == "planning_depth":
            lo, hi = KNOB_BOUNDS[knob]
            knobs[knob] = int(min(hi, max(lo, knobs[knob] + rng.choice((-2, -1, 1, 2)))))
        elif knob == "tool_policy":
            knobs[knob] = "deep" if knobs[knob] == "greedy" else "greedy"
        elif knob == "noise_floor":
            lo, hi = KNOB_BOUNDS[knob]
            knobs[knob] = float(min(hi, max(lo, knobs[knob] * rng.choice((0.5, 2.0)))))
    return make_genome(
        parameter_count=knobs["parameter_count"],
        memory_capacity=knobs["memory_capacity"],
        planning_depth=knobs["planning_depth"],
        tool_policy=knobs["tool_policy"],
        noise_floor=knobs["noise_floor"],
        generation=generation,
        parents=(genome.genome_id,),
    )
