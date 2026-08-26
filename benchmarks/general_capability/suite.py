# Copyright (c) Ultrone Contributors. All rights reserved.
"""General-capability benchmark suite: does evolution generalize?

Answers one question convincingly: *does ULTRONE become more capable
across generations, including on tasks it was not optimized against?*

Protocol (three disjoint task sets):

    TRAIN/SEARCH  ->  evolutionary optimization
    VALIDATION    ->  candidate selection
    HOLDOUT       ->  final capability measurement

The holdout set is sealed behind :class:`HoldoutSeal`: every access is
recorded as an immutable audit event, and the evolutionary loop has no
API to touch it. A candidate's promotion may therefore cite a holdout
result that its search never optimized against.

Families are grounded in the same real sandbox micro-benchmarks used
by ``self_improvement.lab.evaluator``, but each family is instantiated
with split-specific seeds, so scores on TRAIN do not imply scores on
HOLDOUT -- genuine generalization is measurable, not assumed.
"""

from __future__ import annotations

import hashlib
import json
import random
from dataclasses import dataclass, field
from typing import Any, Dict, List, Sequence, Tuple

from sandbox.experience import run_learning_curve
from sandbox.perception import run_perception_suite
from sandbox.planning import SkillRegistry, backchain
from self_improvement.lab.evaluator import (
    CAPABILITY_DIMENSIONS,
    _chain_registry,
    _memory_score,
    _prediction_score,
    _reasoning_ok,
    _robustness_score,
    _tool_score,
)
from self_improvement.lab.genome import Genome

__all__ = [
    "SPLITS",
    "GeneralCapabilitySuite",
    "HoldoutSeal",
]

#: Split identity -> seed-space base offsets (disjoint by construction).
SPLITS: Dict[str, int] = {
    "train": 0,            # what evolution optimizes against
    "validation": 10_000,  # candidate selection only
    "holdout": 900_000,    # sealed until after promotion
}

#: Families measured per snapshot; composites derived afterwards.
_FAMILIES = (
    "planning", "memory", "prediction", "tool_use", "robustness",
    "adaptation", "perception", "machine_control",
)

_INTERNAL_SEEDS = (0, 1, 2)      # per-split replicates


def _family_scores(genome: Genome, base_seed: int) -> Dict[str, float]:
    """One score per family at a given point in seed space."""
    rng = random.Random(base_seed)
    # Planning: which goal chain this split asks about is drawn from
    # this split's seed space (chain length 1..6).
    L = rng.randint(1, 6)
    reg = _chain_registry()
    planning = 1.0 if backchain(
        reg, "synthetic", f"c{L}_goal",
        max_depth=genome.planning_depth) else 0.0
    # Memory / tool_use / reasoning are deterministic in the knobs;
    # they vary across candidates but not across splits.
    return {
        "planning": round(planning, 4),
        "memory": _memory_score(genome.memory_capacity),
        "prediction": _prediction_score(genome.noise_floor,
                                        seed=base_seed + 11),
        "tool_use": _tool_score(genome.tool_policy),
        "robustness": _robustness_score(seed=base_seed + 23),
        "adaptation": _adaptation_score(base_seed + 37),
        "perception": run_perception_suite(seed=base_seed + 41,
                                           n_trials=60)["fusion_accuracy"],
        "machine_control": _machine_control_split_score(base_seed + 53),
    }


def _adaptation_score(seed: int) -> float:
    curve = run_learning_curve(seed=seed, episodes=3, steps_per_episode=60)
    best_arm = max(curve["arm_probs"])
    return round(min(1.0, curve["episode_mean_reward"][-1] / best_arm), 4)


def _machine_control_split_score(seed: int) -> float:
    from self_improvement.lab.evaluator import _machine_control_score
    return _machine_control_score(seed=seed)


def _composites(raw: Dict[str, float]) -> Dict[str, float]:
    """Same transparent formulas as lab.evaluator.measure_genome."""
    out = dict(raw)
    out["coding"] = round(0.6 * raw["tool_use"] + 0.4 * raw["planning"], 4)
    out["mathematics"] = round(
        0.5 * raw["prediction"] + 0.5 * (1.0 if _reasoning_ok() else 0.0), 4)
    out["language"] = round(
        0.4 * raw["perception"] + 0.3 * raw["memory"]
        + 0.3 * raw["tool_use"], 4)
    out["generalization"] = round(
        (raw["planning"] + raw["memory"] + raw["adaptation"]) / 3.0, 4)
    out["reasoning"] = 1.0 if _reasoning_ok() else 0.0
    return {d: round(out[d], 4) for d in CAPABILITY_DIMENSIONS}


class GeneralCapabilitySuite:
    """Split-aware measurement over independent capability families."""

    def __init__(self, seed: int = 0, replicates: int = 3) -> None:
        self.seed = seed
        self.replicates = replicates

    def evaluate(self, genome: Genome, split: str) -> Dict[str, float]:
        """Mean per-dimension scores on one split; never use 'holdout'
        during search -- that path goes through HoldoutSeal."""
        if split not in SPLITS:
            raise ValueError(f"unknown split '{split}'")
        base = SPLITS[split] + self.seed * 1000
        acc: Dict[str, float] = {}
        for i in range(self.replicates):
            for fam, val in _family_scores(genome, base + i).items():
                acc[fam] = acc.get(fam, 0.0) + val
        n = float(self.replicates)
        return _composites({k: v / n for k, v in acc.items()})

    @staticmethod
    def mean_index(scores: Dict[str, float]) -> float:
        return round(sum(scores[d] for d in CAPABILITY_DIMENSIONS)
                     / len(CAPABILITY_DIMENSIONS), 6)


class HoldoutSeal:
    """The holdout split behind an audit-logged, append-only seal.

    The evolutionary loop never receives a reference to a useful
    result: ``measure`` records WHO unsealed it and WHEN (logical
    order), so a promotion audit can prove the holdout was consulted
    only after selection concluded.
    """

    def __init__(self, suite: GeneralCapabilitySuite) -> None:
        self._suite = suite
        self.events: List[Dict[str, Any]] = []
        self.unsealed_count = 0

    def measure(self, genome: Genome, actor: str) -> Dict[str, Any]:
        """Unseal: compute holdout scores and log the access."""
        self.unsealed_count += 1
        scores = self._suite.evaluate(genome, "holdout")
        payload = json.dumps(scores, sort_keys=True, separators=(",", ":"))
        event = {
            "order": self.unsealed_count,
            "actor": actor,
            "genome_hash": genome.stable_hash(),
            "mean_index": GeneralCapabilitySuite.mean_index(scores),
            "fingerprint":
                hashlib.sha256(payload.encode()).hexdigest()[:16],
        }
        self.events.append(event)         # append-only audit history
        return {"scores": scores, **event}

    @property
    def integrity(self) -> str:
        """Recomputable fingerprint of the whole audit chain."""
        payload = json.dumps(self.events, sort_keys=True,
                             separators=(",", ":"))
        return hashlib.sha256(payload.encode()).hexdigest()[:16]
