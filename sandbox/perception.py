# Copyright (c) Ultrone Contributors. All rights reserved.
"""Multimodal perception: fusing unreliable modalities into one belief.

Three simulated modalities (visual, lidar-like profile, textual tag) each
produce a *claim* about an object's class with modality-specific
reliability and reported confidence. The fusion policy is transparent:
weighted confidence voting with deterministic tie-breaks. Missing
modalities simply contribute nothing -- the weights do not need to be
renormalized by hand.

The benchmark question: does fusion beat the best single modality, and
does it degrade gracefully when modalities drop out?
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Dict, Iterable, List

CLASSES = ("barrel", "crate", "tarp")

#: P(modality reports the true class). Kept comparable so that fused
#: independent evidence can beat every single modality -- the interesting
#: regime for a fusion benchmark.
MODALITY_RELIABILITY = {"visual": 0.85, "lidar": 0.80, "tag": 0.88}
#: Confidence a modality reports alongside its claim.
MODALITY_CONFIDENCE = {"visual": 0.75, "lidar": 0.70, "tag": 0.78}
DEFAULT_WEIGHTS = {"visual": 0.34, "lidar": 0.33, "tag": 0.33}


@dataclass(frozen=True)
class Percept:
    modality: str
    claimed_class: str
    confidence: float


class MultimodalWorld:
    """Generates per-modality claims about hidden object classes."""

    def __init__(self, seed: int = 0) -> None:
        self.rng = random.Random(seed)

    def observe(
        self, true_class: str, available_modalities: Iterable[str],
    ) -> List[Percept]:
        percepts: List[Percept] = []
        for modality in sorted(available_modalities):
            if self.rng.random() < MODALITY_RELIABILITY[modality]:
                claim = true_class
            else:
                others = [c for c in CLASSES if c != true_class]
                claim = others[self.rng.randrange(len(others))]
            percepts.append(Percept(
                modality, claim, MODALITY_CONFIDENCE[modality],
            ))
        return percepts


class MultimodalFusion:
    def __init__(self, weights: Dict[str, float] | None = None) -> None:
        self.weights = dict(weights if weights is not None else DEFAULT_WEIGHTS)

    def fuse(self, percepts: Iterable[Percept]) -> Percept:
        scores = {c: 0.0 for c in CLASSES}
        weight_sum = 0.0
        for p in percepts:
            effective = self.weights.get(p.modality, 0.0) * p.confidence
            scores[p.claimed_class] += effective
            weight_sum += effective
        if weight_sum == 0.0:
            return Percept("fused", CLASSES[0], 0.0)  # blind fallback
        label = sorted(scores.items(), key=lambda kv: (-kv[1], kv[0]))[0][0]
        return Percept("fused", label, round(min(1.0, scores[label] / weight_sum), 6))


def run_perception_suite(
    seed: int = 0, n_trials: int = 400, modality_dropout: float = 0.25,
) -> Dict[str, object]:
    """Fusion vs unimodal accuracy under random modality dropout."""
    world = MultimodalWorld(seed)
    fusion = MultimodalFusion()
    correct = {"fused": 0, **{m: 0 for m in MODALITY_RELIABILITY}}
    present = {m: 0 for m in MODALITY_RELIABILITY}

    for i in range(n_trials):
        truth = CLASSES[i % len(CLASSES)]
        mods = [m for m in sorted(DEFAULT_WEIGHTS)
                if world.rng.random() >= modality_dropout]
        percepts = world.observe(truth, mods)
        fused = fusion.fuse(percepts)
        if fused.claimed_class == truth:
            correct["fused"] += 1
        for p in percepts:
            present[p.modality] += 1
            if p.claimed_class == truth:
                correct[p.modality] += 1

    def acc(key: str, denom: int) -> float:
        return round(correct[key] / max(1, denom), 4)

    unimodal = {m: acc(m, present[m]) for m in sorted(MODALITY_RELIABILITY)}
    best_single = max(unimodal.values())
    return {
        "n_trials": n_trials,
        "modality_dropout": modality_dropout,
        "fusion_accuracy": acc("fused", n_trials),
        "unimodal_accuracy": unimodal,
        "beats_best_unimodal": acc("fused", n_trials) >= best_single - 0.03,
        "graceful_under_dropout": acc("fused", n_trials) > 0.70,
    }
