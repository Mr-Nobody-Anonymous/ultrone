# Neural Milestone: the 5 missing pieces

This directory closes the gap flagged in the project charter between
two distinct capability questions:

> "Did my controlled learner improve under deterministic simulation?"

vs

> "Can an actual neural model plug into the same pipeline and improve?"

The previous benchmark (`benchmarks.self_training_benchmark`) answered
the **simulated** question. The code here answers the **neural**
question -- on the *same* orchestration, the *same* `ModelAdapter`
seam, the *same* `LearnedWeights` lineage, the *same* `compare_capabilities`
evaluation. None of the surrounding control architecture is touched.

## The five pieces

| # | Component                                | File              | What it does |
|---|------------------------------------------|-------------------|--------------|
| 1 | Real model adapter                       | `adapters.py`     | `MockNeuralAdapter` + `NeuralAdapterConfig`. The deterministic test double that responds to LoRA updates; the production targets (`HostedModelAdapter`, `LocalModelAdapter`) already exist in `self_improvement.self_training.adapters` and slot in unchanged. |
| 2 | Tokenizer + model pipeline               | `pipeline.py`     | `ModelPipeline` (protocol contract) + `DeterministicTestPipeline` (test implementation). Handles load, tokenize, batch, generate-batch, save/load checkpoint. |
| 3 | LoRA / parameter-efficient fine-tuning   | `lora_trainer.py` | `LoRATrainer` fits an adapter delta on top of a `NeuralLearnedWeights`. The result *is* a `LearnedWeights` (subclass) so the existing checkpoint + promotion + regression + capability-comparison code keeps working. |
| 4 | Real training dataset                    | `dataset.py`      | `ExternalCorpus` (curated / public / synthetic / experience) + `DatasetSplitter` (deterministic train/holdout split with leakage detection). The same `TrainingExample` schema the existing `DatasetBuilder` already emits, so `ContinualMixture` can merge external + experience without modification. |
| 5 | Neural capability benchmark              | `benchmark.py`    | `NeuralCapabilityBenchmark` runs base vs candidate under **both** a simulated and a neural adapter, and reports them on *separate* `CapabilitySourceReport`s -- never merged. |

## Hard rule this module enforces

A "simulated" gain is evidence the *surround* improved on the
simulated task mix; it is **not** evidence the underlying neural
model became more intelligent. The benchmark never merges the two
into one "got smarter" claim. If you only promote on the simulated
report, you are not promoting a real model.

## How to use

```python
from self_improvement.neural import (
    NeuralAdapterConfig,
    MockNeuralAdapter,
    DeterministicTestPipeline,
    ExternalCorpus,
    DatasetSplitter,
    LoRATrainer,
    NeuralLearnedWeights,
    NeuralCapabilityBenchmark,
)

# 1. Adapter + pipeline
config = NeuralAdapterConfig(model_id="my-model")
pipeline = DeterministicTestPipeline(config).load()

# 2. Build a base model
base = NeuralLearnedWeights(
    values={"reasoning": 0.5, "coding": 0.5,
            "retrieval": 0.5, "tool_use": 0.5},
    config_fingerprint=config.fingerprint(),
    base_model_hash="base",
)

# 3. Curate a real dataset
corpus = ExternalCorpus(
    name="v1", kind="curated",
    examples=my_examples, split="train",
    source="my-team",
)

# 4. Split + train
splitter = DatasetSplitter(train_ratio=0.75, seed=42)
split = splitter.split(corpus.records(), tag="v1")
trainer = LoRATrainer(rank=8, alpha=16.0,
                      learning_rate=0.1, steps=5, seed=42)
candidate = trainer.fit(
    base=base,
    examples=split.pair.train.load(),
    dataset_hash=split.pair.train.content_hash,
    config_fingerprint=config.fingerprint(),
).weights

# 5. Benchmark
report = NeuralCapabilityBenchmark(
    cycles=5, family_each=4, split_seed=42,
).run()
print(report.simulated.measurably_better)  # surround
print(report.neural.measurably_better)      # actual model
```

## End-to-end demo

A runnable demo that exercises all 5 pieces lives at
`scripts/run_neural_milestone.py`. Run it from the repo root:

```bash
python scripts/run_neural_milestone.py
```

It prints the separate simulated and neural reports and exits with a
machine-readable JSON dump for downstream tooling.

## Tests

`tests/test_neural_module.py` (63 tests) covers:

* `NeuralAdapterConfig` validation and fingerprint stability
* `MockNeuralAdapter` determinism, clamping, stats, adapter injection
* `TokenizerSpec` + `DeterministicTestPipeline` load / tokenize / batch / generate / checkpoint round-trip
* `NeuralLearnedWeights` validation, `to_config` / `from_config` round-trip (neural *and* legacy kind)
* `LoRATrainer` loss trend, determinism, no-signal-no-delta, safety bound
* `ExternalCorpus` records preservation, kind validation
* `DatasetSplitter` total preservation, determinism, partition coverage, ratio validation
* `NeuralCapabilityBenchmark` simulated+neural separation, determinism, JSON serialisation, train/holdout hash divergence

## Honest scope

This is a **test rig**. `MockNeuralAdapter` is a deterministic
behaviour stand-in: it answers the same `ModelAdapter` contract a
real local LLM would answer, it responds to a LoRA delta, and it
records per-call stats -- but it does not load weights. To go from
this rig to a real model, swap `MockNeuralAdapter` for
`LocalModelAdapter` (already in `self_improvement.self_training.adapters`)
and the rest of the pipeline -- `ModelPipeline`, `LoRATrainer`,
`DatasetSplitter`, `NeuralCapabilityBenchmark` -- does not change.
