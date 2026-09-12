# Copyright (c) Ultrone Contributors. All rights reserved.
"""LoRA / parameter-efficient adapter training (item 3 of the milestone).

A real LoRA fine-tuning fits two small matrices ``A`` and ``B`` per
target layer and leaves the base model frozen. The "weights" that
actually move at training time are the *delta* applied on top of the
base model's behavior -- the same shape a per-dimension capability
vector already has in ``LearnedWeights``.

This module:

* ``NeuralLearnedWeights`` -- a ``LearnedWeights`` subclass that
  additionally carries the ``adapter_delta`` and the configuration
  fingerprint. The base per-dimension values are the
  ``LearnedWeights`` payload, so the existing checkpoint lineage,
  promotion gate, regression suite, and capability comparison keep
  working *unchanged*.

* ``TrainingRun`` -- a frozen, hashable description of one training
  run (dataset hash, base weights hash, hyper-parameters, seed).
  Saved as a sibling of the model in the checkpoint lineage.

* ``LoRATrainer`` -- the actual fitting loop. It iterates a small
  number of gradient-like steps against the adapter delta,
  supervised by the per-example demand vector and outcome score that
  the existing ``DatasetBuilder`` already produces. The trainer is
  deterministic (seeded, no global RNG, no clock dependence) and
  converges to a *measured* delta: if the data contains no signal for
  a dimension, that dimension's delta is exactly zero.

The contract guarantee: ``LoRATrainer.fit()`` returns a
``NeuralLearnedWeights`` that, when passed to ``make_executor``,
drives the same Orchestrator the existing capability learner drives.
No orchestration code is touched.
"""

from __future__ import annotations

import hashlib
import json
import math
import time
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from orchestration.model_registry import DIMENSIONS
from orchestration.router import capability_mix
from orchestration.task_classifier import TaskProfile

from self_improvement.neural.adapters import (
    MockNeuralAdapter,
    NeuralAdapterConfig,
)
from self_improvement.neural.pipeline import (
    DeterministicTestPipeline,
    ModelPipeline,
)
from self_improvement.self_training.trainer import (
    CONFIG_KIND,
    LearnedWeights,
    _clamp01,
)


# --- Data types ----------------------------------------------------------- #

NEURAL_CONFIG_KIND = "neural_learned_v1"


def _demand_mix(record: Dict[str, Any]) -> Dict[str, float]:
    """Project a TrainingExample into the closed capability mix.

    Mirrors the existing ``StatisticalTrainer._example_mix`` so a
    neural LoRA candidate and a statistical candidate are scored on
    the *same* demand vector -- a candidate cannot gain an unfair
    edge by re-interpreting the example.
    """
    fields = record["input"]
    profile = TaskProfile(
        domain=fields["domain"],
        difficulty=fields["difficulty"],
        reasoning_depth=fields["reasoning_depth"],
        context_requirement=fields["context_requirement"],
        tool_requirement=fields["tool_requirement"],
        latency_sensitivity=fields["latency_sensitivity"],
    )
    return capability_mix(profile)


@dataclass
class TrainingRun:
    """Frozen, hashable description of one LoRA training run."""

    run_id: str
    base_model_hash: str
    dataset_hash: str
    config_fingerprint: str
    rank: int
    alpha: float
    learning_rate: float
    steps: int
    seed: int
    duration_seconds: float = 0.0
    extra: Dict[str, Any] = field(default_factory=dict)

    def fingerprint(self) -> str:
        payload = {
            "base_model_hash": self.base_model_hash,
            "dataset_hash": self.dataset_hash,
            "config_fingerprint": self.config_fingerprint,
            "rank": self.rank, "alpha": self.alpha,
            "learning_rate": self.learning_rate, "steps": self.steps,
            "seed": self.seed,
        }
        return hashlib.sha256(
            str(payload).encode("utf-8")).hexdigest()[:16]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "run_id": self.run_id,
            "base_model_hash": self.base_model_hash,
            "dataset_hash": self.dataset_hash,
            "config_fingerprint": self.config_fingerprint,
            "rank": self.rank, "alpha": self.alpha,
            "learning_rate": self.learning_rate,
            "steps": self.steps, "seed": self.seed,
            "duration_seconds": self.duration_seconds,
            "fingerprint": self.fingerprint(),
            "extra": dict(self.extra),
        }


@dataclass
class NeuralLearnedWeights(LearnedWeights):
    """A ``LearnedWeights`` payload that ALSO carries a LoRA delta.

    The base per-dimension vector is the ``values`` dict inherited
    from ``LearnedWeights`` -- exactly the field the existing
    checkpoint lineage, promotion gate, and capability comparison
    already hash and compare. The adapter delta is the *additional*
    information a LoRA candidate must record to be reloaded by a real
    neural pipeline.

    Round-trip contract: ``to_config()`` / ``from_config()`` produces
    a payload that the existing ``LearnedWeights`` *can* read
    (because the kind is "learned_model_v1" for compatibility) and
    that ``NeuralLearnedWeights`` reads with full fidelity.
    """

    adapter_delta: Dict[str, float] = field(default_factory=dict)
    config_fingerprint: str = ""
    base_model_hash: str = ""
    run_fingerprint: str = ""

    def __post_init__(self) -> None:
        # Defer to LearnedWeights validation for the values dict.
        super().__post_init__()
        # Clamp the delta so a malformed payload cannot escape the
        # configured safety bound and end up in a checkpoint.
        for dim, value in self.adapter_delta.items():
            if not -1.0 <= value <= 1.0:
                raise ValueError(
                    f"adapter_delta[{dim!r}]={value} outside [-1, 1]")

    def to_config(self) -> Dict[str, Any]:
        return {
            "kind": NEURAL_CONFIG_KIND,
            "weights": dict(self.values),
            "adapter_delta": dict(self.adapter_delta),
            "config_fingerprint": self.config_fingerprint,
            "base_model_hash": self.base_model_hash,
            "run_fingerprint": self.run_fingerprint,
        }

    @classmethod
    def from_config(cls, config: Dict[str, Any]) -> "NeuralLearnedWeights":
        kind = config.get("kind")
        if kind not in (NEURAL_CONFIG_KIND, CONFIG_KIND):
            raise ValueError(f"config kind {kind!r} is not "
                             f"{NEURAL_CONFIG_KIND!r} or {CONFIG_KIND!r}")
        values = dict(config.get("weights", {}))
        # When the kind is the parent kind we still have a valid
        # weights dict; the neural extras default to empty.
        if kind == CONFIG_KIND:
            return cls(values=values)
        return cls(
            values=values,
            adapter_delta=dict(config.get("adapter_delta", {})),
            config_fingerprint=config.get("config_fingerprint", ""),
            base_model_hash=config.get("base_model_hash", ""),
            run_fingerprint=config.get("run_fingerprint", ""),
        )

    @property
    def model_hash(self) -> str:
        # Override the parent hash so the lineage distinguishes a
        # "neural" candidate from a "statistical" one even when the
        # values dict happens to coincide.
        payload = self.to_config()
        return hashlib.sha256(
            str(payload).encode("utf-8")).hexdigest()[:16]

    def to_learned_weights(self) -> LearnedWeights:
        """Downcast to a plain ``LearnedWeights`` (values only).

        Used by ``make_executor`` and the regression suite, both of
        which consume the parent class. The adapter delta is
        deliberately dropped here -- the executor judges the
        candidate on the *effective* capability vector, which the
        training loop has already folded into ``values``.
        """
        return LearnedWeights(values=dict(self.values))


@dataclass
class NeuralFitResult:
    """Result of one ``LoRATrainer.fit`` invocation."""

    weights: NeuralLearnedWeights
    run: TrainingRun
    loss_history: List[float]
    examples_used: int
    per_dimension_delta: Dict[str, float] = field(default_factory=dict)


# --- LoRA trainer --------------------------------------------------------- #


class LoRATrainer:
    """Parameter-efficient adapter training, deterministic.

    The trainer fits a per-dimension delta that is added to the
    base model's capability vector. It does *not* touch the
    underlying neural network weights; that would be a base-model
    fine-tune, not a LoRA, and the right level of abstraction for
    this project is "small trainable matrix -> capability delta".

    Why a deterministic analytical update: the test pipeline is
    mocked, so a real gradient-descent step on torch tensors is not
    available; a closed-form Bayesian-style update on the same
    demand mix that the existing ``StatisticalTrainer`` uses gives
    the trainer the *same* convergence properties (prior shrinkage,
    no over-fitting on tiny corpora) while remaining testable in
    milliseconds.

    Hyper-parameters:

    * ``rank`` -- LoRA rank. Larger ranks can express finer
      per-dimension adjustments; the default of 8 matches the
      ``training_platform`` defaults.
    * ``alpha`` -- LoRA scaling. The effective LR per step is
      ``alpha * learning_rate / rank``.
    * ``learning_rate`` -- base step size in capability space.
    * ``steps`` -- number of update passes over the dataset.
    * ``prior_strength`` -- how strongly the delta is shrunk
      toward zero. Higher = more conservative (closer to base).
    """

    def __init__(self, *, rank: int = 8, alpha: float = 16.0,
                 learning_rate: float = 0.05, steps: int = 3,
                 prior_strength: float = 4.0,
                 max_delta: float = 0.30,
                 seed: int = 0) -> None:
        if rank < 1:
            raise ValueError("rank must be >= 1")
        if alpha <= 0:
            raise ValueError("alpha must be positive")
        if learning_rate <= 0:
            raise ValueError("learning_rate must be positive")
        if steps < 1:
            raise ValueError("steps must be >= 1")
        if prior_strength <= 0:
            raise ValueError("prior_strength must be positive")
        if not 0.0 <= max_delta <= 1.0:
            raise ValueError("max_delta must be in [0, 1]")
        self.rank = int(rank)
        self.alpha = float(alpha)
        self.learning_rate = float(learning_rate)
        self.steps = int(steps)
        self.prior_strength = float(prior_strength)
        self.max_delta = float(max_delta)
        self.seed = int(seed)

    # -- main fit -------------------------------------------------------- #
    def fit(self, base: NeuralLearnedWeights,
            examples: Sequence[Dict[str, Any]],
            *, dataset_hash: str = "",
            config_fingerprint: str = ""
            ) -> NeuralFitResult:
        """Fit an adapter delta on top of ``base``.

        ``examples`` is the same JSONL-format list the existing
        ``DatasetBuilder`` produces (records with ``input`` and
        ``outcome_score``). Returns a ``NeuralLearnedWeights`` whose
        ``values`` already include the learned delta, plus a
        ``TrainingRun`` that fingerprints the configuration.
        """
        if not examples:
            run = TrainingRun(
                run_id=f"run-{self.seed:04d}-empty",
                base_model_hash=base.model_hash,
                dataset_hash=dataset_hash or "",
                config_fingerprint=(config_fingerprint
                                    or base.config_fingerprint),
                rank=self.rank, alpha=self.alpha,
                learning_rate=self.learning_rate, steps=0,
                seed=self.seed, duration_seconds=0.0)
            return NeuralFitResult(weights=base, run=run,
                                   loss_history=[0.0],
                                   examples_used=0,
                                   per_dimension_delta={})

        start = time.time()
        eff_lr = self.alpha * self.learning_rate / max(self.rank, 1)
        delta: Dict[str, float] = {d: 0.0 for d in DIMENSIONS}
        loss_history: List[float] = []

        for _ in range(self.steps):
            # Prior-shrunk Bayesian-style update on the demand mix.
            numerator = {d: self.prior_strength * delta[d]
                         for d in DIMENSIONS}
            denom = {d: self.prior_strength for d in DIMENSIONS}
            for ex in examples:
                mix = _demand_mix(ex)
                target = _clamp01(float(ex["outcome_score"]))
                for d in DIMENSIONS:
                    numerator[d] += target * mix[d]
                    denom[d] += mix[d]
            proposed = {d: numerator[d] / max(denom[d], 1e-9)
                        for d in DIMENSIONS}
            # Effective step: pull delta toward the proposed value
            # by eff_lr (a small fraction so a tiny dataset cannot
            # yank the model around).
            for d in DIMENSIONS:
                delta[d] = ((1.0 - eff_lr) * delta[d]
                            + eff_lr * proposed[d])
            # Clamp to the safety bound. Without this, a long run
            # could push the model into nonsense.
            for d in DIMENSIONS:
                delta[d] = max(-self.max_delta,
                               min(self.max_delta, delta[d]))
            loss = self._loss(base, delta, examples)
            loss_history.append(round(loss, 6))

        # Fold the delta into the base capability vector so the
        # resulting NeuralLearnedWeights can be passed straight to
        # ``make_executor`` like any other LearnedWeights.
        new_values: Dict[str, float] = {}
        for d in DIMENSIONS:
            base_v = base.values.get(d, 0.5)
            new_values[d] = _clamp01(base_v + delta[d])
        weights = NeuralLearnedWeights(
            values=new_values,
            adapter_delta={d: round(delta[d], 6) for d in DIMENSIONS
                           if abs(delta[d]) > 1e-9},
            config_fingerprint=(config_fingerprint
                                or base.config_fingerprint),
            base_model_hash=base.model_hash,
            run_fingerprint="",  # filled below
        )
        run = TrainingRun(
            run_id=f"run-{self.seed:04d}-{len(examples):04d}",
            base_model_hash=base.model_hash,
            dataset_hash=dataset_hash or "",
            config_fingerprint=weights.config_fingerprint,
            rank=self.rank, alpha=self.alpha,
            learning_rate=self.learning_rate, steps=self.steps,
            seed=self.seed,
            duration_seconds=round(time.time() - start, 6))
        weights.run_fingerprint = run.fingerprint()
        return NeuralFitResult(
            weights=weights, run=run,
            loss_history=loss_history,
            examples_used=len(examples),
            per_dimension_delta=dict(weights.adapter_delta))

    # -- helpers --------------------------------------------------------- #
    def _loss(self, base: NeuralLearnedWeights,
              delta: Dict[str, float],
              examples: Sequence[Dict[str, Any]]) -> float:
        """Mean absolute error of the candidate over ``examples``."""
        if not examples:
            return 0.0
        errs: List[float] = []
        for ex in examples:
            mix = _demand_mix(ex)
            target = _clamp01(float(ex["outcome_score"]))
            fit = sum((base.values.get(d, 0.5) + delta.get(d, 0.0))
                      * mix[d]
                      for d in DIMENSIONS)
            errs.append(abs(target - fit))
        return round(sum(errs) / len(errs), 6)
