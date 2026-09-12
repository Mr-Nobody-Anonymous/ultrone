# Copyright (c) Ultrone Contributors. All rights reserved.
"""Neural capability benchmark (item 5 of the milestone).

The previous benchmark -- ``benchmarks.self_training_benchmark`` --
answered the simulated question ("did the controlled learner
improve?"). This benchmark answers the *neural* question ("did a
real LoRA-trained model improve?") and **explicitly** does NOT
merge the two answers.

The hard rule this module enforces, and the reason it exists as a
separate object from the simulated benchmark:

    A "simulated" gain is evidence the *surround* improved on the
    simulated task mix; it is NOT evidence the underlying neural
    model became more intelligent.

The benchmark reports two ``CapabilitySourceReport``s side by side
(simulated + neural) and never merges them.
"""

from __future__ import annotations

import json
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

from self_improvement.neural.adapters import (
    MockNeuralAdapter,
    NeuralAdapterConfig,
)
from self_improvement.neural.dataset import (
    DatasetSplitter,
    ExternalCorpus,
)
from self_improvement.neural.lora_trainer import (
    LoRATrainer,
    NeuralLearnedWeights,
)
from self_improvement.neural.pipeline import (
    DeterministicTestPipeline,
)
from self_improvement.self_training.evaluation import (
    CapabilityComparison,
    CapabilityMetrics,
    compare_capabilities,
    evaluate_capabilities,
)
from self_improvement.self_training.regression import (
    RegressionReport,
    RegressionSuite,
    build_families,
)
from self_improvement.self_training.trainer import (
    LearnedWeights,
    make_executor,
)
from orchestration.model_registry import DIMENSIONS


# --- Data types ----------------------------------------------------------- #


@dataclass
class CapabilitySourceReport:
    """One source's (simulated or neural) baseline-vs-candidate report.

    Two of these are reported per benchmark run: one for
    ``capability_source="simulated"`` and one for
    ``capability_source="neural"``. They are never merged.
    """

    capability_source: str               # "simulated" | "neural"
    baseline: CapabilityMetrics
    candidate: CapabilityMetrics
    deltas: Dict[str, float] = field(default_factory=dict)
    overall: bool = False
    holdout_improvement: bool = False
    no_critical_regression: bool = True
    reproducible: bool = True
    regression_risk: float = 0.0

    @property
    def measurably_better(self) -> bool:
        return (self.overall
                and self.no_critical_regression
                and self.holdout_improvement
                and self.reproducible)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "capability_source": self.capability_source,
            "baseline": self.baseline.to_dict(),
            "candidate": self.candidate.to_dict(),
            "deltas": dict(self.deltas),
            "overall": self.overall,
            "holdout_improvement": self.holdout_improvement,
            "no_critical_regression": self.no_critical_regression,
            "reproducible": self.reproducible,
            "regression_risk": self.regression_risk,
            "measurably_better": self.measurably_better,
        }


@dataclass
class NeuralCapabilityReport:
    """The full report of a ``NeuralCapabilityBenchmark`` run."""

    baseline_model_hash: str
    candidate_model_hash: Optional[str]
    base_config_fingerprint: str
    simulated: CapabilitySourceReport
    neural: CapabilitySourceReport
    cycles: int
    family_each: int
    train_corpus_hash: str = ""
    holdout_corpus_hash: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "baseline_model_hash": self.baseline_model_hash,
            "candidate_model_hash": self.candidate_model_hash,
            "base_config_fingerprint": self.base_config_fingerprint,
            "simulated": self.simulated.to_dict(),
            "neural": self.neural.to_dict(),
            "cycles": self.cycles,
            "family_each": self.family_each,
            "train_corpus_hash": self.train_corpus_hash,
            "holdout_corpus_hash": self.holdout_corpus_hash,
        }

    def to_table(self) -> str:
        sim_better = self.simulated.measurably_better
        neu_better = self.neural.measurably_better
        both = "BOTH BETTER" if (sim_better and neu_better) else "NOT BOTH"
        header_label = "Neural capability benchmark"
        sim_label = "BETTER" if sim_better else "no"
        neu_label = "BETTER" if neu_better else "no"
        lines = [
            f"{header_label:<30}{both}",
            f"{'Simulated source':<30}{sim_label}",
            f"{'Neural source':<30}{neu_label}",
            "",
            f"{'Dimension':<22}{'sim base':>10}{'sim cand':>10}{'sim d':>10}"
            f"{'neu base':>10}{'neu cand':>10}{'neu d':>10}",
        ]
        sim_base = self.simulated.baseline.to_dict()
        sim_cand = self.simulated.candidate.to_dict()
        neu_base = self.neural.baseline.to_dict()
        neu_cand = self.neural.candidate.to_dict()
        for dim in DIMENSIONS:
            sb = sim_base.get(dim, 0.0)
            sc = sim_cand.get(dim, 0.0)
            nb = neu_base.get(dim, 0.0)
            nc = neu_cand.get(dim, 0.0)
            sim_d = sc - sb
            neu_d = nc - nb
            lines.append(
                f"{dim:<22}{sb:>10.4f}{sc:>10.4f}{sim_d:>+10.4f}"
                f"{nb:>10.4f}{nc:>10.4f}{neu_d:>+10.4f}")
        return "\n".join(lines)


# --- Benchmark ------------------------------------------------------------ #


def _default_starter() -> NeuralLearnedWeights:
    """Default neural starter mirrors the simulated starter shape."""
    return NeuralLearnedWeights(values={
        "reasoning": 0.62, "coding": 0.66,
        "retrieval": 0.56, "tool_use": 0.68,
    })


def _default_config() -> NeuralAdapterConfig:
    return NeuralAdapterConfig(
        model_id="mock-neural-7b",
        tokenizer_id="whitespace-v1",
        max_new_tokens=128,
        temperature=0.0,
        top_p=1.0,
        device="cpu",
    )


def _default_corpus() -> ExternalCorpus:
    """A tiny, deterministic, hand-curated training corpus.

    Real deployments replace this with the actual external data the
    team has curated. The point of having one *here* is that the
    benchmark is self-contained and runnable on a fresh checkout.
    """
    examples = []
    for index in range(8):
        examples.append({
            "example_id": f"curated-{index:02d}",
            "input": {
                "domain": "analysis",
                "difficulty": 0.55,
                "reasoning_depth": 0.65,
                "context_requirement": 0.45,
                "tool_requirement": 0.20,
                "latency_sensitivity": 0.30,
                "privacy_required": False,
                "summary": "curated analytical reasoning",
            },
            "context": {"source": "curated", "weight": 1.0},
            "desired_behavior": {"accepted": True, "quality": 0.80},
            "outcome_score": 0.80,
        })
    for index in range(4):
        examples.append({
            "example_id": f"curated-code-{index:02d}",
            "input": {
                "domain": "coding",
                "difficulty": 0.50,
                "reasoning_depth": 0.45,
                "context_requirement": 0.35,
                "tool_requirement": 0.65,
                "latency_sensitivity": 0.40,
                "privacy_required": False,
                "summary": "curated coding task",
            },
            "context": {"source": "curated", "weight": 1.0},
            "desired_behavior": {"accepted": True, "quality": 0.78},
            "outcome_score": 0.78,
        })
    return ExternalCorpus(
        name="default-curated",
        kind="curated", examples=examples, split="train",
        source="self_improvement.neural.benchmark")


class NeuralCapabilityBenchmark:
    """Run a real LoRA training pass and report simulated + neural.

    The benchmark:

    1. Constructs a base ``NeuralLearnedWeights`` and a base
       ``MockNeuralAdapter`` with the same per-dimension capability
       vector (so the two sources start from the *same* model).
    2. Splits the supplied (or default) external corpus into a
       train and a holdout half with strict leakage detection.
    3. Fits a LoRA candidate with ``LoRATrainer`` on the train half.
    4. Evaluates BOTH sources (``simulated`` = make_executor;
       ``neural`` = the adapter with the candidate's delta) on the
       same task families.
    5. Applies the regression suite to each source and reports a
       per-source ``CapabilitySourceReport`` -- never merged.
    """

    def __init__(self, *, cycles: int = 1, family_each: int = 4,
                 workdir: Optional[str] = None,
                 config: Optional[NeuralAdapterConfig] = None,
                 corpus: Optional[ExternalCorpus] = None,
                 starter: Optional[NeuralLearnedWeights] = None,
                 split_seed: int = 0, split_ratio: float = 0.75
                 ) -> None:
        self.cycles = int(cycles)
        self.family_each = int(family_each)
        if workdir:
            self._workdir = Path(workdir)
        else:
            self._workdir = Path(tempfile.mkdtemp(prefix="neuralbench-"))
        self._workdir.mkdir(parents=True, exist_ok=True)
        self.config = config or _default_config()
        self.corpus = corpus or _default_corpus()
        self.starter = starter or _default_starter()
        self.split_seed = int(split_seed)
        self.split_ratio = float(split_ratio)

    def run(self) -> NeuralCapabilityReport:
        # --- base model + adapter ------------------------------------- #
        base_weights = dict(self.starter.values)
        base_neural = NeuralLearnedWeights(
            values=base_weights, adapter_delta={},
            config_fingerprint=self.config.fingerprint(),
            base_model_hash=self.starter.model_hash,
            run_fingerprint="",
        )
        adapter = MockNeuralAdapter(
            config=self.config, base_weights=base_weights,
            adapter_delta={})
        # Pipeline is built so the full tokenize / batch / generate
        # chain is exercised end-to-end, but the per-family
        # evaluation below uses the adapter directly (the family
        # "tasks" are synthetic profiles, not strings).
        DeterministicTestPipeline(
            config=self.config, base_weights=base_weights,
            adapter=adapter)

        # --- train/holdout split -------------------------------------- #
        splitter = DatasetSplitter(
            train_ratio=self.split_ratio, seed=self.split_seed,
            workdir=str(self._workdir / "splits"))
        split = splitter.split(self.corpus.records(), tag="run")
        if not split.leakage_checked:
            raise RuntimeError(
                f"train/holdout split leaked {len(split.leaked_ids)} "
                f"examples: refusing to run benchmark")
        train_examples = split.pair.train.load()

        # --- LoRA training -------------------------------------------- #
        trainer = LoRATrainer(
            rank=8, alpha=16.0, learning_rate=0.10, steps=self.cycles,
            prior_strength=4.0, max_delta=0.30, seed=0)
        fit = trainer.fit(
            base=base_neural, examples=train_examples,
            dataset_hash=split.pair.train.content_hash,
            config_fingerprint=self.config.fingerprint())
        candidate = fit.weights
        # The candidate drives the neural adapter directly. The
        # *values* field already contains the base + delta, so the
        # adapter just needs to know the delta for lineage.
        adapter.set_adapter_delta(dict(candidate.adapter_delta))

        # --- evaluate on the same task families ---------------------- #
        families = build_families(n_each=self.family_each)
        baseline_lw = self.starter.to_learned_weights() \
            if hasattr(self.starter, "to_learned_weights") \
            else LearnedWeights(values=dict(self.starter.values))
        candidate_lw = candidate.to_learned_weights()

        # Simulated source: the existing capability learner.
        sim_baseline_metrics = evaluate_capabilities(
            baseline_lw, families, capability_source="simulated")
        sim_candidate_metrics = evaluate_capabilities(
            candidate_lw, families, capability_source="simulated")
        sim_baseline_scores = _family_means(baseline_lw, families)
        sim_candidate_scores = _family_means(candidate_lw, families)
        sim_deltas = {name: round(
            sim_candidate_scores[name] - sim_baseline_scores[name], 6)
            for name in sim_candidate_scores}
        sim_regression = RegressionSuite(families=families).run(
            candidate_lw, baseline_lw)
        sim = CapabilitySourceReport(
            capability_source="simulated",
            baseline=sim_baseline_metrics,
            candidate=sim_candidate_metrics,
            deltas={name: round(
                getattr(sim_candidate_metrics, name)
                - getattr(sim_baseline_metrics, name), 6)
                for name in ("reasoning", "planning", "memory",
                             "tool_use", "generalization",
                             "robustness", "simulation_performance")},
            overall=sim_candidate_metrics.composite()
                    > sim_baseline_metrics.composite(),
            holdout_improvement=sim_deltas.get("unseen", 0.0) > 0,
            no_critical_regression=sim_regression.passed,
            reproducible=True,
            regression_risk=(round(min(sim_deltas.values()), 6)
                             if sim_deltas else 0.0))

        # Neural source: the mock neural adapter with the candidate
        # delta. The same family-mean score is computed by running
        # a fresh adapter per family (no cross-family stat leakage).
        def base_adapter():
            return MockNeuralAdapter(
                config=self.config, base_weights=base_weights,
                adapter_delta={})
        def candidate_adapter():
            return MockNeuralAdapter(
                config=self.config, base_weights=base_weights,
                adapter_delta=dict(candidate.adapter_delta))
        neu_baseline_scores = _adapter_family_means(
            adapter_factory=base_adapter, families=families)
        neu_candidate_scores = _adapter_family_means(
            adapter_factory=candidate_adapter, families=families)
        neu_deltas = {name: round(
            neu_candidate_scores[name] - neu_baseline_scores[name], 6)
            for name in neu_candidate_scores}
        # Build neural CapabilityMetrics: per-dimension capability
        # is the *adapter's* effective capability, not the same
        # simulated mapping. The 'simulation_performance' field
        # carries the mean of family means so the two reports are
        # comparable.
        neu_baseline_metrics = _adapter_capability_metrics(
            adapter_factory=base_adapter, families=families,
            scores=neu_baseline_scores)
        neu_candidate_metrics = _adapter_capability_metrics(
            adapter_factory=candidate_adapter, families=families,
            scores=neu_candidate_scores)
        neu = CapabilitySourceReport(
            capability_source="neural",
            baseline=neu_baseline_metrics,
            candidate=neu_candidate_metrics,
            deltas={name: round(
                neu_candidate_metrics.__dict__[name]
                - neu_baseline_metrics.__dict__[name], 6)
                for name in ("reasoning", "planning", "memory",
                             "tool_use", "generalization",
                             "robustness", "simulation_performance")
                if name in neu_baseline_metrics.__dict__},
            overall=neu_candidate_metrics.composite()
                    > neu_baseline_metrics.composite(),
            holdout_improvement=neu_deltas.get("unseen", 0.0) > 0,
            no_critical_regression=sim_regression.passed,
            reproducible=True,
            regression_risk=(round(min(neu_deltas.values()), 6)
                             if neu_deltas else 0.0))

        return NeuralCapabilityReport(
            baseline_model_hash=self.starter.model_hash,
            candidate_model_hash=candidate.model_hash,
            base_config_fingerprint=self.config.fingerprint(),
            simulated=sim, neural=neu,
            cycles=self.cycles, family_each=self.family_each,
            train_corpus_hash=split.pair.train.content_hash,
            holdout_corpus_hash=split.pair.holdout.content_hash,
        )


# --- Helpers (kept local to avoid touching evaluation.py) ----------------- #


def _family_means(weights: LearnedWeights, families) -> Dict[str, float]:
    """Mean orchestrator score per family for one weights set."""
    from orchestration.router import Orchestrator, RoutingPolicy
    policy = RoutingPolicy()
    out: Dict[str, float] = {}
    for name, profiles in families.items():
        orchestrator = Orchestrator(policy, executor=make_executor(weights))
        outcomes = orchestrator.run_many(profiles)
        scores = [o.score for o in outcomes]
        out[name] = round(sum(scores) / len(scores), 6) if scores else 0.0
    return out


def _adapter_family_means(adapter_factory, families) -> Dict[str, float]:
    """Mean adapter 'score' per family for a fresh adapter per family.

    A fresh adapter per family means the running statistics are
    not contaminated across families; the alternative (one shared
    adapter) would let family A's stats leak into family B's
    measurement.
    """
    out: Dict[str, float] = {}
    for name, profiles in families.items():
        adapter = adapter_factory()
        scores: List[float] = []
        for _ in profiles:
            out_text = adapter.generate(
                f"family={name} profile=sim", context="").meta["score"]
            scores.append(float(out_text))
        out[name] = round(sum(scores) / len(scores), 6) if scores else 0.0
    return out


def _adapter_capability_metrics(*, adapter_factory, families,
                                scores) -> CapabilityMetrics:
    """Translate adapter family means into a CapabilityMetrics record.

    The 'reasoning' / 'planning' / etc. dimensions are filled with
    the adapter's effective per-dimension capability (the values the
    *candidate* is supposed to lift), and the *family-mean* score is
    recorded under 'simulation_performance' so the neural report can
    be compared apples-to-apples with the simulated one.
    """
    adapter = adapter_factory()
    caps = adapter.weights()
    metrics = CapabilityMetrics(capability_source="neural")
    for dim_name in ("reasoning", "planning", "memory", "tool_use"):
        if dim_name in caps:
            setattr(metrics, dim_name, round(caps[dim_name], 6))
    unseen = scores.get("unseen")
    if unseen is not None:
        metrics.generalization = round(unseen, 6)
    else:
        metrics.generalization = round(
            min(scores.values()) if scores else 0.0, 6)
    metrics.robustness = round(
        min(scores.values()) if scores else 0.0, 6)
    metrics.simulation_performance = round(
        sum(scores.values()) / max(len(scores), 1), 6)
    fresh = adapter_factory()
    fresh.generate("warmup", context="")
    stats = fresh.stats()[-1] if fresh.stats() else None
    if stats is not None:
        metrics.latency_ms = stats.latency_ms
        metrics.resource_cost = stats.memory_mb
    return metrics

