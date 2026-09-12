#!/usr/bin/env python
"""End-to-end demonstration: the 5-piece neural milestone in action.

This script answers the question

    "Can a real neural model plug into the same pipeline and improve?"

in three layers:

  1. Build a ``MockNeuralAdapter`` (item 1) and a
     ``DeterministicTestPipeline`` (item 2) so the
     ``ModelAdapter`` seam is exercised end-to-end.
  2. Build a small ``ExternalCorpus`` (item 4), split it into
     train + holdout, and fit a LoRA candidate with ``LoRATrainer``
     (item 3).
  3. Run ``NeuralCapabilityBenchmark`` (item 5) and print a
     separate simulated vs neural report -- never merged.

Run from the repo root:

    python scripts/run_neural_milestone.py

The output is human-readable on purpose: it shows exactly what
the milestone proves and what it does *not* prove.
"""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from self_improvement.neural.adapters import (
    MockNeuralAdapter, NeuralAdapterConfig,
)
from self_improvement.neural.benchmark import (
    NeuralCapabilityBenchmark,
)
from self_improvement.neural.dataset import (
    DatasetSplitter, ExternalCorpus,
)
from self_improvement.neural.lora_trainer import (
    LoRATrainer, NeuralLearnedWeights,
)
from self_improvement.neural.pipeline import (
    DeterministicTestPipeline,
)
from self_improvement.self_training.dataset_builder import (
    TrainingExample,
)
from orchestration.model_registry import DIMENSIONS


# --------------------------------------------------------------------------- #
# 1. Build a model + tokenizer pipeline
# --------------------------------------------------------------------------- #


def build_model_and_pipeline(model_id="mock-neural-7b"):
    config = NeuralAdapterConfig(
        model_id=model_id,
        tokenizer_id="whitespace-v1",
        max_new_tokens=64,
        temperature=0.0,
        top_p=1.0,
        device="cpu",
        dtype="float32",
    )
    base_weights = {
        "reasoning": 0.55, "coding": 0.60,
        "retrieval": 0.50, "tool_use": 0.65,
    }
    pipeline = DeterministicTestPipeline(
        config=config, base_weights=base_weights,
    )
    pipeline.load()
    return config, base_weights, pipeline


# --------------------------------------------------------------------------- #
# 2. Build an external training corpus
# --------------------------------------------------------------------------- #


def build_corpus(n_per_kind=8, outcome=0.85):
    examples = []
    # Mix of analytical and coding examples, with strict train/holdout
    # tagging at the corpus level (not the example level).
    for i in range(n_per_kind):
        examples.append(TrainingExample(
            example_id=f"analytical-{i:02d}",
            input={"domain": "analysis", "difficulty": 0.55,
                    "reasoning_depth": 0.65,
                    "context_requirement": 0.45,
                    "tool_requirement": 0.20,
                    "latency_sensitivity": 0.30},
            context={"source": "demo", "weight": 1.0},
            desired_behavior={"accepted": True, "quality": outcome},
            outcome_score=outcome,
        ))
    for i in range(n_per_kind):
        examples.append(TrainingExample(
            example_id=f"code-{i:02d}",
            input={"domain": "coding", "difficulty": 0.50,
                    "reasoning_depth": 0.45,
                    "context_requirement": 0.35,
                    "tool_requirement": 0.65,
                    "latency_sensitivity": 0.40},
            context={"source": "demo", "weight": 1.0},
            desired_behavior={"accepted": True, "quality": outcome},
            outcome_score=outcome,
        ))
    return ExternalCorpus(
        name="demo-corpus", kind="curated",
        examples=examples, split="train",
        source="run_neural_milestone.py",
    )


# --------------------------------------------------------------------------- #
# 3. Print a single CapabilitySourceReport
# --------------------------------------------------------------------------- #


def print_source(label, report):
    print(f"  [{label}] capability_source = {report.capability_source!r}")
    print(f"  [{label}] measurably_better   = {report.measurably_better}")
    print(f"  [{label}] overall            = {report.overall}")
    print(f"  [{label}] holdout_improvement= {report.holdout_improvement}")
    print(f"  [{label}] no_critical_regress= {report.no_critical_regression}")
    print(f"  [{label}] reproducible       = {report.reproducible}")
    print(f"  [{label}] per-dim deltas:")
    for k, v in sorted(report.deltas.items()):
        sign = "+" if v >= 0 else ""
        print(f"      {k:>22}: {sign}{v:+.4f}")


# --------------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------------- #


def main():
    print("=" * 70)
    print(" ULTRONE neural-milestone end-to-end demo")
    print("='\''Can a real neural model plug into the same pipeline and improve?\'\''")
    print("=" * 70)

    # Item 1 + 2: model adapter + tokenizer pipeline.
    print()
    print("[1/5] Real model adapter (MockNeuralAdapter) + config")
    config, base_weights, pipeline = build_model_and_pipeline()
    print(f"      model_id         = {config.model_id!r}")
    print(f"      config fingerprint = {config.fingerprint()}")
    base_adapter = MockNeuralAdapter(
        config=config, base_weights=base_weights, adapter_delta={},
    )
    sample = base_adapter.generate("hello", context="ctx")
    print(f"      sample output    = {sample.text[:60]!r}...")

    print()
    print("[2/5] Tokenizer + model pipeline (DeterministicTestPipeline)")
    ex = pipeline.tokenize("demo-1", "hello world pipeline")
    batch = pipeline.batch([ex])
    results = pipeline.generate_batch(batch)
    print(f"      tokenize produced {len(ex.input_ids)} ids")
    print(f"      batch size        = {len(results)}")
    print(f"      pipeline loaded   = {pipeline.is_loaded()}")

    # Item 4: real training dataset with strict train/holdout split.
    print()
    print("[3/5] Real training dataset (ExternalCorpus + DatasetSplitter)")
    corpus = build_corpus()
    print(f"      corpus size        = {len(corpus)}")
    print(f"      corpus fingerprint= {corpus.fingerprint()}")
    with tempfile.TemporaryDirectory() as d:
        splitter = DatasetSplitter(
            train_ratio=0.75, seed=42, workdir=d,
        )
        split = splitter.split(corpus.records(), tag="demo")
        print(f"      leakage_checked    = {split.leakage_checked}")
        print(f"      train rows         = {split.pair.train.num_examples}")
        print(f"      holdout rows       = {split.pair.holdout.num_examples}")
        print(f"      train hash         = {split.pair.train.content_hash}")
        print(f"      holdout hash       = {split.pair.holdout.content_hash}")

        # Item 3: LoRA training on the train half.
        print()
        print("[4/5] LoRA / adapter training (LoRATrainer)")
        base_neural = NeuralLearnedWeights(
            values=dict(base_weights),
            config_fingerprint=config.fingerprint(),
            base_model_hash="demo-base",
        )
        trainer = LoRATrainer(
            rank=8, alpha=16.0, learning_rate=0.10, steps=5,
            prior_strength=4.0, max_delta=0.30, seed=42,
        )
        fit = trainer.fit(
            base=base_neural,
            examples=split.pair.train.load(),
            dataset_hash=split.pair.train.content_hash,
            config_fingerprint=config.fingerprint(),
        )
        candidate = fit.weights
        print(f"      candidate model_hash = {candidate.model_hash}")
        print(f"      base model_hash      = {base_neural.model_hash}")
        print(f"      run fingerprint      = {candidate.run_fingerprint}")
        print(f"      loss trajectory      = {fit.loss_history}")
        print(f"      per-dim delta:")
        for k, v in sorted(candidate.adapter_delta.items()):
            sign = "+" if v >= 0 else ""
            print(f"          {k:>10}: {sign}{v:+.4f}")

    # Item 5: benchmark -- simulated and neural reported side by side.
    print()
    print("[5/5] Neural capability benchmark (simulated + neural)")
    bench = NeuralCapabilityBenchmark(
        cycles=5, family_each=4, split_seed=42, workdir=d,
    )
    report = bench.run()
    print()
    print("  baseline model hash :", report.baseline_model_hash)
    print("  candidate model hash:", report.candidate_model_hash)
    print("  train corpus hash   :", report.train_corpus_hash)
    print("  holdout corpus hash :", report.holdout_corpus_hash)
    print()
    print_source("simulated", report.simulated)
    print()
    print_source("neural", report.neural)
    print()
    print("-" * 70)
    print(" IMPORTANT -- the two sources are NEVER merged.")
    print(" A 'simulated' gain is evidence the *surround* improved;")
    print(" it is NOT evidence the underlying neural model became")
    print(" more intelligent. Promotion must look at the 'neural'")
    print(" report alone.")
    print("-" * 70)

    # Always print a machine-readable summary too.
    print()
    print(json.dumps(report.to_dict(), default=str, indent=2))


if __name__ == "__main__":
    main()
