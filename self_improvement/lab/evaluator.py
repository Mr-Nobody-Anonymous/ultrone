# Copyright (c) Ultrone Contributors. All rights reserved.
"""CapabilitySnapshot: the measurable "how good is this candidate" object.

Every dimension is grounded in a REAL sandbox micro-benchmark -- no
invented scores:

- planning       -- backward-chaining success over synthetic goal chains of
                    length 2..7 at the genome's planning depth;
- memory         -- continual-learning retention given its capacity;
- prediction     -- Brier score of its belief agent (noise-floor knob);
- tool_use       -- easy + hard tool-chain goals under its search policy;
- perception     -- multimodal fusion accuracy under dropout;
- robustness     -- boundedness under mild distribution shift;
- adaptation     -- bandit learning-curve convergence to the best arm;
- reasoning      -- cross-domain deduction + analogy (platform-level).

``coding`` / ``mathematics`` / ``language`` / ``generalization`` are
transparent composites of the measured dimensions (documented formulas).
Efficiency is capability per unit of parameter budget: a smaller
candidate matching a bigger one's capability WINS.
"""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass
from typing import Any, Dict

from sandbox.continual import build_task_sequence, run_continual_sequence
from sandbox.experience import run_learning_curve
from sandbox.perception import run_perception_suite
from sandbox.planning import Skill, SkillRegistry, backchain
from sandbox.prediction import BayesianBeliefAgent, PredictionBenchmark

CAPABILITY_DIMENSIONS = (
    "reasoning", "planning", "memory", "perception", "coding",
    "mathematics", "prediction", "tool_use", "language", "adaptation",
    "generalization", "robustness", "machine_control",
)


def _chain_registry() -> SkillRegistry:
    """Goal chains of total skill-length 2..7 (root has empty premises)."""
    reg = SkillRegistry()
    for L in range(1, 7):                       # L+1 skills needed incl. goal
        prev = f"c{L}_0"
        reg.register(Skill(f"c{L}_root", "synthetic", frozenset(), prev))
        for i in range(1, L):
            nxt = f"c{L}_{i}"
            reg.register(Skill(f"c{L}_step{i}", "synthetic",
                               frozenset({prev}), nxt))
            prev = nxt
        reg.register(Skill(f"c{L}_final", "synthetic",
                           frozenset({prev}), f"c{L}_goal"))
    return reg


def _planning_score(depth: int) -> float:
    reg = _chain_registry()
    solved = sum(
        1 for L in range(1, 7)
        if backchain(reg, "synthetic", f"c{L}_goal", max_depth=depth)
    )
    return round(solved / 6.0, 4)


def _memory_score(capacity: int) -> float:
    tasks = build_task_sequence(4, 4)
    report = run_continual_sequence(tasks, n_train_reps=12,
                                    capacities=(capacity,))
    learners = report["learners"]
    label = next(iter(learners))
    retention = learners[label]["retention_after_all"]
    return round(sum(retention) / len(retention), 4)


def _prediction_score(noise_floor: float, seed: int = 3) -> float:
    from sandbox.robustness import BASE_EMISSIONS

    def factory():
        return BayesianBeliefAgent(
            sorted(BASE_EMISSIONS), BASE_EMISSIONS, noise_floor=noise_floor,
        )

    bench = PredictionBenchmark(factory, BASE_EMISSIONS, seed=seed, n_ticks=40)
    records = bench.run()
    brier = sum(r.brier for r in records) / len(records)
    return round(max(0.0, min(1.0, 1.0 - brier * 4.0)), 4)


def _tool_score(policy: str) -> float:
    from sandbox.tooluse import Tool, build_demo_toolbox

    box = build_demo_toolbox()
    box.register(Tool("top_of_set", "set", "insight",
                      lambda s: sorted(s)[0] if s else ""))
    max_len = 4 if policy == "deep" else 2
    easy = box.chain("text", "count", max_len=max_len)
    hard = box.chain("text", "insight", max_len=max_len)
    score = (1.0 if easy else 0.0) * 0.5
    if hard:
        value = box.execute("beta alpha gamma", hard)
        score += 0.5 if value == "alpha" else 0.0
    return round(score, 4)


def _robustness_score(seed: int = 3) -> float:
    from sandbox.prediction import make_bayesian
    from sandbox.robustness import BASE_EMISSIONS, shift

    factory = make_bayesian(BASE_EMISSIONS)

    def brier(rows):
        bench = PredictionBenchmark(factory, rows, seed=seed, n_ticks=40)
        recs = bench.run()
        return sum(r.brier for r in recs) / len(recs)

    base = brier(shift("base"))
    mild = brier(shift("mild"))
    degradation = (mild - base) / max(base, 1e-9)
    return round(max(0.0, min(1.0, 1.0 - degradation)), 4)


def _reasoning_ok() -> bool:
    from sandbox.reasoning import run_reasoning_suite

    return bool(run_reasoning_suite()["both_domains_solved"])


def _machine_control_score(seed: int = 7) -> float:
    """Fraction of factory-floor tasks settled, halved on any violation."""
    from sandbox.machines import run_machine_control_suite

    report = run_machine_control_suite(seed=seed)
    tasks = report["tasks"]
    settled_fraction = (
        sum(1 for t in tasks.values() if t["settled"]) / len(tasks)
    )
    if not report["zero_hard_violations"]:
        settled_fraction *= 0.5          # unsafe operation is never free
    return round(settled_fraction, 4)


@dataclass(frozen=True)
class CapabilitySnapshot:
    candidate_id: str
    parent_id: str
    generation: int
    architecture: Dict[str, Any]
    capabilities: Dict[str, float]
    resource: Dict[str, float]
    regressions: tuple = ()
    fingerprint: str = ""

    @property
    def capability_index(self) -> float:
        return round(
            sum(self.capabilities[d] for d in CAPABILITY_DIMENSIONS)
            / len(CAPABILITY_DIMENSIONS), 6,
        )

    @property
    def efficiency(self) -> float:
        """Capability per log10-parameters (in millions)."""
        params_m = self.resource["parameter_count"] / 1e6
        return round(
            self.capability_index / max(1.0, math.log10(params_m)), 6,
        )

    def summary(self) -> Dict[str, Any]:
        return {
            "candidate_id": self.candidate_id,
            "generation": self.generation,
            "capability_index": self.capability_index,
            "efficiency": self.efficiency,
            "capabilities": dict(sorted(self.capabilities.items())),
            "resource": dict(sorted(self.resource.items())),
            "regressions": list(self.regressions),
        }


def measure_genome(genome: Genome, seed: int = 0) -> CapabilitySnapshot:
    """Run every micro-benchmark for one genome; fully deterministic."""
    perception = run_perception_suite(
        seed=seed + 5, n_trials=120)["fusion_accuracy"]
    curve = run_learning_curve(seed=seed, episodes=3, steps_per_episode=80)
    best_arm = max(curve["arm_probs"])
    adaptation = min(1.0, curve["episode_mean_reward"][-1] / best_arm)

    raw = {
        "reasoning": 1.0 if _reasoning_ok() else 0.0,
        "planning": _planning_score(genome.planning_depth),
        "memory": _memory_score(genome.memory_capacity),
        "perception": round(perception, 4),
        "prediction": _prediction_score(genome.noise_floor),
        "tool_use": _tool_score(genome.tool_policy),
        "robustness": _robustness_score(seed=seed + 3),
        "adaptation": round(adaptation, 4),
        "machine_control": _machine_control_score(seed=seed + 7),
    }
    # Transparent composites (no hidden parameters):
    raw["coding"] = round(0.6 * raw["tool_use"] + 0.4 * raw["planning"], 4)
    raw["mathematics"] = round(
        0.5 * raw["prediction"] + 0.5 * raw["reasoning"], 4)
    raw["language"] = round(
        0.4 * raw["perception"] + 0.3 * raw["memory"]
        + 0.3 * raw["tool_use"], 4)
    raw["generalization"] = round(
        (raw["planning"] + raw["memory"] + raw["adaptation"]) / 3.0, 4)
    capabilities = {d: raw[d] for d in CAPABILITY_DIMENSIONS}

    latency_proxy = round(
        5.0 + genome.planning_depth * 8.0
        + (genome.parameter_count / 1e8) * 3.0
        + (2.0 if genome.tool_policy == "deep" else 0.0), 3)

    snapshot = CapabilitySnapshot(
        candidate_id=genome.genome_id,
        parent_id=";".join(genome.parents),
        generation=genome.generation,
        architecture=dict(genome.knobs()),
        capabilities=capabilities,
        resource={
            "parameter_count": genome.parameter_count,
            "latency_ms_proxy": latency_proxy,
            "memory_units": round(
                genome.memory_capacity + genome.parameter_count / 1e8, 3),
        },
    )
    payload = json.dumps({
        "caps": capabilities, "res": snapshot.resource,
        "arch": snapshot.architecture,
    }, sort_keys=True, separators=(",", ":"))
    digest = hashlib.sha256(payload.encode()).hexdigest()[:16]
    return CapabilitySnapshot(
        candidate_id=snapshot.candidate_id, parent_id=snapshot.parent_id,
        generation=snapshot.generation, architecture=snapshot.architecture,
        capabilities=capabilities, resource=snapshot.resource,
        fingerprint=digest,
    )

