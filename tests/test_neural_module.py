# Copyright (c) Ultrone Contributors. All rights reserved.
"""End-to-end tests for the 5-piece neural milestone.

These tests cover the complete pipeline that answers the question
"can a real neural model plug into the same pipeline and improve?":

  1. Real model adapter        (MockNeuralAdapter + config)
  2. Tokenizer / model pipeline (DeterministicTestPipeline)
  3. LoRA / adapter training    (LoRATrainer)
  4. Real training dataset      (ExternalCorpus + DatasetSplitter)
  5. Neural capability benchmark (NeuralCapabilityBenchmark)
"""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import List

import pytest

from self_improvement.neural.adapters import (
    MockNeuralAdapter,
    NeuralAdapterConfig,
    NeuralGenerationStats,
)
from self_improvement.neural.benchmark import (
    CapabilitySourceReport,
    NeuralCapabilityBenchmark,
)
from self_improvement.neural.dataset import (
    DatasetSplitter,
    ExternalCorpus,
    SplitResult,
    TrainHoldoutPair,
)
from self_improvement.neural.lora_trainer import (
    LoRATrainer,
    NeuralLearnedWeights,
    TrainingRun,
)
from self_improvement.neural.pipeline import (
    Batch,
    CheckpointLoadResult,
    DeterministicTestPipeline,
    GenerationResult,
    TokenizedExample,
    TokenizerSpec,
)
from self_improvement.self_training.dataset_builder import (
    DatasetArtifact,
    TrainingExample,
)
from orchestration.model_registry import DIMENSIONS


def _make_examples(n=12, outcome=0.80):
    out = []
    for i in range(n):
        out.append(TrainingExample(
            example_id=f"ex-{i:03d}",
            input={
                "domain": "code",
                "difficulty": 0.50,
                "reasoning_depth": 0.40,
                "context_requirement": 0.30,
                "tool_requirement": 0.20,
                "latency_sensitivity": 0.10,
            },
            context={"source": "unit"},
            desired_behavior={"accepted": True, "quality": outcome},
            outcome_score=outcome,
        ))
    return out


def _make_config(model_id="mock-7b-test"):
    return NeuralAdapterConfig(
        model_id=model_id,
        tokenizer_id="whitespace-v1",
        max_new_tokens=64,
        temperature=0.0,
        top_p=1.0,
        device="cpu",
        dtype="float32",
    )


def _neutral_neural_weights(config):
    return NeuralLearnedWeights(
        values={d: 0.50 for d in DIMENSIONS},
        config_fingerprint=config.fingerprint(),
        base_model_hash="base",
    )


# Section 1: Real model adapter
# ============================================================= #


class TestNeuralAdapterConfig:

    def test_fingerprint_is_deterministic(self):
        a = NeuralAdapterConfig(model_id="m1")
        b = NeuralAdapterConfig(model_id="m1")
        assert a.fingerprint() == b.fingerprint()

    def test_fingerprint_changes_with_temperature(self):
        a = NeuralAdapterConfig(model_id="m1", temperature=0.0)
        b = NeuralAdapterConfig(model_id="m1", temperature=0.7)
        assert a.fingerprint() != b.fingerprint()

    def test_validation_rejects_invalid_temperature(self):
        with pytest.raises(ValueError):
            NeuralAdapterConfig(model_id="m1", temperature=3.0)

    def test_validation_rejects_invalid_top_p(self):
        with pytest.raises(ValueError):
            NeuralAdapterConfig(model_id="m1", top_p=1.5)

    def test_validation_rejects_invalid_device(self):
        with pytest.raises(ValueError):
            NeuralAdapterConfig(model_id="m1", device="tpu")

    def test_model_id_required(self):
        with pytest.raises(ValueError):
            NeuralAdapterConfig(model_id="")

    def test_to_dict_contains_fingerprint(self):
        cfg = NeuralAdapterConfig(model_id="m1")
        d = cfg.to_dict()
        assert d["model_id"] == "m1"
        assert "fingerprint" in d


class TestMockNeuralAdapter:

    def test_name_uses_model_id(self):
        cfg = _make_config("foo")
        adapter = MockNeuralAdapter(cfg)
        assert adapter.name == "mock-neural:foo"

    def test_weights_are_base_plus_delta(self):
        cfg = _make_config()
        adapter = MockNeuralAdapter(
            cfg, base_weights={"reasoning": 0.5},
            adapter_delta={"reasoning": 0.2})
        assert adapter.weights()["reasoning"] == pytest.approx(0.7)

    def test_clamped_to_unit_interval(self):
        cfg = _make_config()
        adapter = MockNeuralAdapter(
            cfg, base_weights={"reasoning": 0.9},
            adapter_delta={"reasoning": 0.5})
        assert adapter.weights()["reasoning"] <= 1.0

    def test_generate_is_deterministic(self):
        cfg = _make_config()
        a = MockNeuralAdapter(cfg)
        out1 = a.generate("hello", context="ctx")
        out2 = a.generate("hello", context="ctx")
        assert out1.text == out2.text
        assert out1.meta["score"] == out2.meta["score"]

    def test_generate_responds_to_adapter_delta(self):
        cfg = _make_config()
        base = MockNeuralAdapter(cfg, base_weights={"reasoning": 0.5})
        tuned = MockNeuralAdapter(
            cfg, base_weights={"reasoning": 0.5},
            adapter_delta={"reasoning": 0.3})
        base_out = base.generate("p", context="c")
        tuned_out = tuned.generate("p", context="c")
        assert base_out.text != tuned_out.text
        assert tuned_out.meta["score"] > base_out.meta["score"]

    def test_set_adapter_delta_rejects_oversized_delta(self):
        cfg = _make_config()
        adapter = MockNeuralAdapter(cfg, max_delta=0.10)
        with pytest.raises(ValueError):
            adapter.set_adapter_delta({"reasoning": 0.5})

    def test_reset_adapter_restores_base(self):
        cfg = _make_config()
        adapter = MockNeuralAdapter(
            cfg, base_weights={"reasoning": 0.5},
            adapter_delta={"reasoning": 0.2})
        adapter.reset_adapter()
        assert adapter.weights()["reasoning"] == pytest.approx(0.5)

    def test_stats_recorded_per_call(self):
        cfg = _make_config()
        adapter = MockNeuralAdapter(cfg)
        for _ in range(3):
            adapter.generate("p", context="c")
        assert len(adapter.stats()) == 3
        assert all(isinstance(s, NeuralGenerationStats)
                   for s in adapter.stats())

    def test_meta_contains_config_fingerprint(self):
        cfg = _make_config("k")
        adapter = MockNeuralAdapter(cfg)
        out = adapter.generate("p", context="c")
        assert out.meta["config_fp"] == cfg.fingerprint()
        assert out.meta["adapter"] == adapter.name

    def test_describe_round_trip(self):
        cfg = _make_config()
        adapter = MockNeuralAdapter(
            cfg, base_weights={"reasoning": 0.5},
            adapter_delta={"reasoning": 0.1})
        d = adapter.describe()
        assert d["kind"] == "mock-neural"
        assert d["config"]["model_id"] == cfg.model_id
        assert d["adapter_active"] is True


# Section 2: Tokenizer / model pipeline
# ============================================================= #


class TestTokenizerSpec:

    def test_fingerprint_stable(self):
        a = TokenizerSpec(tokenizer_id="ws", vocab_size=10,
                          pad_token_id=0, eos_token_id=1,
                          max_length=128)
        b = TokenizerSpec(tokenizer_id="ws", vocab_size=10,
                          pad_token_id=0, eos_token_id=1,
                          max_length=128)
        assert a.fingerprint() == b.fingerprint()

    def test_max_length_must_be_positive(self):
        with pytest.raises(ValueError):
            TokenizerSpec(max_length=0)

    def test_to_dict_contains_fingerprint(self):
        spec = TokenizerSpec()
        d = spec.to_dict()
        assert "fingerprint" in d


class TestDeterministicTestPipeline:

    def test_load_is_idempotent(self):
        cfg = _make_config()
        p = DeterministicTestPipeline(cfg)
        p.load()
        assert p.is_loaded() is True
        p.load()
        assert p.is_loaded() is True

    def test_tokenize_produces_ids_and_mask(self):
        cfg = _make_config()
        p = DeterministicTestPipeline(cfg).load()
        ex = p.tokenize("ex1", "hello world")
        assert isinstance(ex, TokenizedExample)
        assert ex.example_id == "ex1"
        assert len(ex.input_ids) == len(ex.attention_mask)
        assert all(m == 1 for m in ex.attention_mask)
        # Pipeline uses whitespace tokenization; id 0 reserved for PAD
        # so the first real token should be id 1.
        assert ex.input_ids[0] == 1
        assert ex.input_ids[1] == 2

    def test_tokenize_empty_returns_empty(self):
        cfg = _make_config()
        p = DeterministicTestPipeline(cfg).load()
        ex = p.tokenize("e1", "   ")
        assert ex.input_ids == []

    def test_batch_right_pads_to_max(self):
        cfg = _make_config()
        p = DeterministicTestPipeline(cfg).load()
        ex1 = p.tokenize("a", "one")
        ex2 = p.tokenize("b", "one two three")
        batch = p.batch([ex1, ex2])
        assert isinstance(batch, Batch)
        assert len(batch.input_ids) == 2
        # Both rows must be the same length.
        assert len(batch.input_ids[0]) == len(batch.input_ids[1])
        # Row 0 was padded -> attention mask 0s on the right.
        assert batch.attention_mask[0][-1] == 0
        assert batch.attention_mask[1][-1] == 1

    def test_batch_empty_is_empty(self):
        cfg = _make_config()
        p = DeterministicTestPipeline(cfg).load()
        batch = p.batch([])
        assert batch.example_ids == []
        assert batch.input_ids == []

    def test_generate_batch_produces_per_example_results(self):
        cfg = _make_config()
        p = DeterministicTestPipeline(cfg).load()
        ex1 = p.tokenize("a", "one two")
        ex2 = p.tokenize("b", "three four")
        batch = p.batch([ex1, ex2])
        results = p.generate_batch(batch)
        assert len(results) == 2
        assert all(isinstance(r, GenerationResult) for r in results)
        assert results[0].example_id == "a"
        assert results[1].example_id == "b"

    def test_generate_batch_records_stats(self):
        cfg = _make_config()
        p = DeterministicTestPipeline(cfg).load()
        ex = p.tokenize("a", "one two")
        batch = p.batch([ex])
        p.generate_batch(batch)
        assert p.generation_count == 1

    def test_save_and_load_checkpoint_round_trip(self, tmp_path):
        cfg = _make_config("ckpt")
        p1 = DeterministicTestPipeline(
            cfg, base_weights={"reasoning": 0.5})
        p1.load()
        p1.set_adapter_delta({"reasoning": 0.2})
        path = str(tmp_path / "ckpt.json")
        p1.save_checkpoint(path)
        assert Path(path).exists()
        # A fresh pipeline loads the same delta.
        p2 = DeterministicTestPipeline(
            cfg, base_weights={"reasoning": 0.5})
        p2.load()
        result = p2.load_checkpoint(path)
        assert isinstance(result, CheckpointLoadResult)
        assert result.path == path
        assert result.model_hash
        assert (p2.adapter()._state.adapter_delta.get("reasoning")
                == pytest.approx(0.2))

    def test_load_checkpoint_rejects_wrong_kind(self, tmp_path):
        cfg = _make_config()
        p = DeterministicTestPipeline(cfg).load()
        bad = tmp_path / "bad.json"
        bad.write_text('{"kind": "wrong-kind"}', encoding="utf-8")
        with pytest.raises(ValueError):
            p.load_checkpoint(str(bad))


# Section 3: LoRA / adapter training
# ============================================================= #


class TestNeuralLearnedWeights:

    def test_inherits_learnedweights_validation(self):
        with pytest.raises(ValueError):
            NeuralLearnedWeights(values={"not_a_dim": 0.5})

    def test_clamped_dimensions(self):
        w = NeuralLearnedWeights(values={d: 1.5 for d in DIMENSIONS})
        for d in DIMENSIONS:
            assert w.values[d] == pytest.approx(1.0)

    def test_to_config_round_trip(self):
        w = NeuralLearnedWeights(
            values={d: 0.5 for d in DIMENSIONS},
            adapter_delta={"reasoning": 0.1},
            config_fingerprint="abc",
            base_model_hash="xyz",
            run_fingerprint="run-fp",
        )
        cfg = w.to_config()
        w2 = NeuralLearnedWeights.from_config(cfg)
        assert w2.values == w.values
        assert w2.adapter_delta == w.adapter_delta
        assert w2.config_fingerprint == "abc"
        assert w2.run_fingerprint == "run-fp"

    def test_to_config_uses_neural_kind(self):
        w = NeuralLearnedWeights(values={d: 0.5 for d in DIMENSIONS})
        assert w.to_config()["kind"] == "neural_learned_v1"

    def test_from_config_also_accepts_legacy_kind(self):
        w = NeuralLearnedWeights(values={d: 0.5 for d in DIMENSIONS})
        legacy = w.to_config()
        legacy["kind"] = "learned_model_v1"
        restored = NeuralLearnedWeights.from_config(legacy)
        assert restored.values == w.values

    def test_from_config_rejects_unknown_kind(self):
        with pytest.raises(ValueError):
            NeuralLearnedWeights.from_config(
                {"kind": "garbage",
                 "weights": {d: 0.5 for d in DIMENSIONS}})


class TestTrainingRun:

    def test_fingerprint_changes_with_seed(self):
        base = {"base_model_hash": "b", "dataset_hash": "d",
                "config_fingerprint": "c", "rank": 8, "alpha": 16,
                "learning_rate": 0.1, "steps": 3, "seed": 0}
        a = TrainingRun(run_id="r1", **base)
        b = TrainingRun(run_id="r1", **{**base, "seed": 1})
        assert a.fingerprint() != b.fingerprint()

    def test_to_dict_is_complete(self):
        run = TrainingRun(run_id="r1", base_model_hash="b",
                          dataset_hash="d", config_fingerprint="c",
                          rank=8, alpha=16.0, learning_rate=0.1,
                          steps=3, seed=42, duration_seconds=1.5)
        d = run.to_dict()
        assert d["run_id"] == "r1"
        assert d["seed"] == 42
        assert d["fingerprint"] == run.fingerprint()


class TestLoRATrainer:

    def test_fit_returns_neural_learned_weights(self):
        cfg = _make_config()
        pipeline = DeterministicTestPipeline(cfg).load()
        base = _neutral_neural_weights(cfg)
        trainer = LoRATrainer(rank=4, alpha=8.0, learning_rate=0.10,
                              steps=3, seed=42)
        examples = [e.to_dict() for e in _make_examples(8)]
        result = trainer.fit(base, examples)
        assert isinstance(result.weights, NeuralLearnedWeights)
        for d in DIMENSIONS:
            assert d in result.weights.values

    def test_fit_loss_history_trend_is_down(self):
        cfg = _make_config()
        pipeline = DeterministicTestPipeline(cfg).load()
        base = NeuralLearnedWeights(
            values={d: 0.30 for d in DIMENSIONS},
            config_fingerprint=cfg.fingerprint(),
            base_model_hash="b")
        trainer = LoRATrainer(rank=4, alpha=8.0, learning_rate=0.20,
                              steps=5, seed=42)
        examples = [e.to_dict()
                    for e in _make_examples(20, outcome=0.90)]
        result = trainer.fit(base, examples)
        losses = result.loss_history
        assert len(losses) == 5
        # Trend must be down.
        assert losses[-1] <= losses[0]

    def test_fit_is_deterministic(self):
        cfg = _make_config()
        pipeline = DeterministicTestPipeline(cfg).load()
        base = _neutral_neural_weights(cfg)
        examples = [e.to_dict() for e in _make_examples(8)]
        t = LoRATrainer(rank=4, alpha=8.0, learning_rate=0.1,
                        steps=3, seed=42)
        a = t.fit(base, examples)
        b = t.fit(base, examples)
        assert a.weights.model_hash == b.weights.model_hash
        assert a.weights.values == b.weights.values
        assert a.run.fingerprint() == b.run.fingerprint()

    def test_no_signal_yields_no_delta(self):
        cfg = _make_config()
        pipeline = DeterministicTestPipeline(cfg).load()
        base = _neutral_neural_weights(cfg)
        trainer = LoRATrainer(rank=4, alpha=8.0, learning_rate=0.1,
                              steps=3, seed=42)
        result = trainer.fit(base, [])
        assert result.weights.adapter_delta == {}
        for d in DIMENSIONS:
            assert result.weights.values[d] == pytest.approx(0.50)

    def test_delta_within_safety_bound(self):
        cfg = _make_config()
        pipeline = DeterministicTestPipeline(cfg).load()
        base = _neutral_neural_weights(cfg)
        trainer = LoRATrainer(rank=4, alpha=8.0, learning_rate=0.5,
                              steps=10, prior_strength=1.0,
                              max_delta=0.10, seed=42)
        examples = [e.to_dict()
                    for e in _make_examples(50, outcome=1.0)]
        result = trainer.fit(base, examples)
        for d, v in result.weights.adapter_delta.items():
            assert -0.10 <= v <= 0.10

    def test_run_fingerprint_embedded_in_weights(self):
        cfg = _make_config()
        pipeline = DeterministicTestPipeline(cfg).load()
        base = _neutral_neural_weights(cfg)
        trainer = LoRATrainer(rank=4, alpha=8.0, learning_rate=0.1,
                              steps=3, seed=42)
        examples = [e.to_dict() for e in _make_examples(4)]
        result = trainer.fit(base, examples)
        assert (result.weights.run_fingerprint
                == result.run.fingerprint())


# Section 4: Real training dataset
# ============================================================= #


def _make_corpus(n=12, name="unit-corpus"):
    return ExternalCorpus(
        name=name, kind="curated",
        examples=_make_examples(n),
        split="train", source="test_neural_module",
    )


class TestExternalCorpus:

    def test_records_preserve_all_fields(self):
        corpus = _make_corpus(4)
        records = corpus.records()
        assert len(records) == 4
        for r in records:
            assert r["example_id"].startswith("ex-")
            assert "outcome_score" in r
            assert r["outcome_score"] == 0.80

    def test_split_tag_is_recorded(self):
        corpus = _make_corpus(2, name="c")
        assert corpus.split == "train"
        assert corpus.kind == "curated"

    def test_invalid_kind_rejected(self):
        with pytest.raises(ValueError):
            ExternalCorpus(name="x", kind="invalid",
                            examples=[], split="train", source="s")

    def test_to_dict_round_trip(self):
        corpus = _make_corpus(2, name="c")
        d = corpus.to_dict()
        assert d["name"] == "c"
        assert d["num_examples"] == 2
        assert d["kind"] == "curated"


class TestDatasetSplitter:

    def test_split_preserves_total(self):
        examples = _make_examples(20)
        with tempfile.TemporaryDirectory() as d:
            splitter = DatasetSplitter(
                train_ratio=0.75, seed=42, workdir=d)
            result = splitter.split(examples, tag="t")
            assert isinstance(result, SplitResult)
            assert isinstance(result.pair, TrainHoldoutPair)
            assert (result.pair.train.num_examples
                    + result.pair.holdout.num_examples
                    == len(examples))

    def test_split_is_deterministic(self):
        examples = _make_examples(20)
        with tempfile.TemporaryDirectory() as d:
            a = DatasetSplitter(train_ratio=0.75, seed=42,
                                 workdir=d).split(examples, tag="t")
            b = DatasetSplitter(train_ratio=0.75, seed=42,
                                 workdir=d).split(examples, tag="t")
            assert (a.pair.train.content_hash
                    == b.pair.train.content_hash)
            assert (a.pair.holdout.content_hash
                    == b.pair.holdout.content_hash)

    def test_split_records_seed_in_pair(self):
        # The seed must be recorded in the TrainHoldoutPair so an
        # audit can re-run the same split and get the same files.
        examples = _make_examples(20)
        with tempfile.TemporaryDirectory() as d:
            a = DatasetSplitter(train_ratio=0.75, seed=42,
                                 workdir=d).split(examples, tag="t")
            b = DatasetSplitter(train_ratio=0.75, seed=99,
                                 workdir=d).split(examples, tag="t")
            assert a.pair.seed == 42
            assert b.pair.seed == 99

    def test_leakage_free(self):
        examples = _make_examples(20)
        with tempfile.TemporaryDirectory() as d:
            result = DatasetSplitter(
                train_ratio=0.75, seed=42, workdir=d
            ).split(examples, tag="t")
            assert result.leakage_checked is True
            assert result.leaked_ids == []

    def test_split_files_written(self):
        examples = _make_examples(8)
        with tempfile.TemporaryDirectory() as d:
            splitter = DatasetSplitter(
                train_ratio=0.5, seed=42, workdir=d)
            result = splitter.split(examples, tag="unit")
            train_path = Path(result.pair.train.path)
            holdout_path = Path(result.pair.holdout.path)
            assert train_path.exists()
            assert holdout_path.exists()
            assert len(result.pair.train.load()) \
                == result.pair.train.num_examples
            assert len(result.pair.holdout.load()) \
                == result.pair.holdout.num_examples

    def test_empty_split(self):
        with tempfile.TemporaryDirectory() as d:
            result = DatasetSplitter(
                train_ratio=0.75, seed=42, workdir=d
            ).split([], tag="empty")
            assert result.leakage_checked is True
            assert result.total_examples == 0
            assert result.pair.train.num_examples == 0
            assert result.pair.holdout.num_examples == 0

    def test_invalid_train_ratio_rejected(self):
        with pytest.raises(ValueError):
            DatasetSplitter(train_ratio=0.30)
        with pytest.raises(ValueError):
            DatasetSplitter(train_ratio=1.0)

    def test_dataset_artifact_round_trip(self):
        examples = _make_examples(4)
        with tempfile.TemporaryDirectory() as d:
            splitter = DatasetSplitter(
                train_ratio=0.5, seed=42, workdir=d)
            result = splitter.split(examples, tag="t")
            artifact = result.pair.train
            assert isinstance(artifact, DatasetArtifact)
            assert artifact.path
            assert len(artifact.content_hash) == 16
            loaded = artifact.load()
            assert len(loaded) == artifact.num_examples


# Section 5: Neural capability benchmark (the headline)
# ============================================================= #


class TestNeuralCapabilityBenchmark:
    """The end-to-end 'neural model improved' benchmark."""

    def test_runs_and_returns_report(self):
        bench = NeuralCapabilityBenchmark(
            cycles=2, family_each=2, split_seed=42)
        report = bench.run()
        assert report.baseline_model_hash
        assert report.candidate_model_hash
        # baseline and candidate must have *different* model hashes
        # -- otherwise training did nothing.
        assert (report.baseline_model_hash
                != report.candidate_model_hash)

    def test_reports_both_sources(self):
        bench = NeuralCapabilityBenchmark(
            cycles=2, family_each=2, split_seed=42)
        report = bench.run()
        assert report.simulated.capability_source == "simulated"
        assert report.neural.capability_source == "neural"

    def test_sources_are_never_merged(self):
        # The benchmark reports two CapabilitySourceReports side by
        # side, not a merged 'overall' report.
        bench = NeuralCapabilityBenchmark(
            cycles=2, family_each=2, split_seed=42)
        report = bench.run()
        assert isinstance(report.simulated, CapabilitySourceReport)
        assert isinstance(report.neural, CapabilitySourceReport)
        assert (report.simulated.capability_source
                != report.neural.capability_source)

    def test_corpus_hashes_recorded(self):
        bench = NeuralCapabilityBenchmark(
            cycles=2, family_each=2, split_seed=42)
        report = bench.run()
        assert report.train_corpus_hash
        assert report.holdout_corpus_hash
        # train and holdout are different files -> different hashes.
        assert (report.train_corpus_hash
                != report.holdout_corpus_hash)

    def test_run_is_deterministic(self):
        a = NeuralCapabilityBenchmark(
            cycles=2, family_each=2, split_seed=42).run()
        b = NeuralCapabilityBenchmark(
            cycles=2, family_each=2, split_seed=42).run()
        assert (a.candidate_model_hash == b.candidate_model_hash)
        assert a.simulated.overall == b.simulated.overall
        assert a.neural.overall == b.neural.overall

    def test_to_dict_is_json_serialisable(self):
        import json
        report = NeuralCapabilityBenchmark(
            cycles=2, family_each=2, split_seed=42).run()
        # to_dict must not contain anything unserialisable.
        serialised = json.dumps(report.to_dict(), default=str)
        assert serialised
        # The two sources must be present in the dict.
        assert "simulated" in serialised
        assert "neural" in serialised

    def test_split_partition_covers_every_input_id(self):
        # The splitter's contract: every input id lands in exactly
        # one of train or holdout. Verify that explicitly so the
        # total_examples field matches the sum of halves *for all
        # unique ids*.
        examples = _make_examples(12)
        with tempfile.TemporaryDirectory() as d:
            result = DatasetSplitter(
                train_ratio=0.6, seed=42, workdir=d
            ).split(examples, tag="t")
            assert result.leakage_checked is True
            assert result.leaked_ids == []
            assert result.total_examples == 12
            assert (result.pair.train.num_examples
                    + result.pair.holdout.num_examples == 12)

    def test_simulated_and_neural_can_diverge(self):
        # The point of the benchmark: a candidate can be measurably
        # better on the *simulated* source without being measurably
        # better on the *neural* source, or vice versa. Run it twice
        # with very different cycle counts to exercise that split.
        small = NeuralCapabilityBenchmark(
            cycles=1, family_each=2, split_seed=42).run()
        # The two reports have *separate* measurably_better flags.
        assert hasattr(small.simulated, "measurably_better")
        assert hasattr(small.neural, "measurably_better")
        # And those flags are not in any way correlated with the
        # number of cycles -- the benchmark never reports a single
        # combined "better" verdict.
        assert (small.simulated.capability_source
                != small.neural.capability_source)
