# Copyright (c) Ultrone Contributors. All rights reserved.
"""Neural model integration layer for the self-training pipeline.

This package closes the gap flagged in the project charter between
"the simulated capability learner improved" and "a real neural model
plugged into the same pipeline improved". It does **not** replace or
duplicate the existing controlled learner -- it sits *alongside* it,
sharing the same ``ModelAdapter`` seam, the same
``LearnedWeights``/``CheckpointManager`` lineage, and the same
``compare_capabilities`` evaluation. The five things it adds:

1. **Real model adapter**        -- ``MockNeuralAdapter`` (deterministic
   test double) + the existing ``HostedModelAdapter`` /
   ``LocalModelAdapter`` already behind ``ModelAdapter``.
2. **Tokenizer/model pipeline**   -- ``ModelPipeline`` (load, batch,
   generate, checkpoint load) with a deterministic test pipeline.
3. **LoRA/adapter training**      -- ``LoRATrainer`` fits a small
   adapter vector that is *also* a ``LearnedWeights`` so the existing
   checkpoint + promotion + regression + capability-comparison code
   keeps working without modification.
4. **Real training dataset**      -- ``ExternalCorpus`` ingestion +
   ``DatasetSplitter`` for strict train/holdout separation; the
   ``DatasetBuilder`` is reused, never duplicated.
5. **Benchmark**                  -- ``NeuralCapabilityBenchmark`` runs
   base vs candidate under BOTH a simulated and a neural adapter, and
   reports them on *separate* capability sources so a surrounding
   improvement is never mistaken for a neural improvement.

The capability-source provenance is the hard rule: a "simulated" gain
is evidence the *surround* improved on the simulated task mix; it is
NOT evidence the underlying neural model became more intelligent. The
benchmark never merges the two into one "got smarter" claim.
"""

from self_improvement.neural.adapters import (
    MockNeuralAdapter,
    NeuralAdapterConfig,
    NeuralGenerationStats,
)
from self_improvement.neural.pipeline import (
    Batch,
    CheckpointLoadResult,
    DeterministicTestPipeline,
    GenerationResult,
    ModelPipeline,
    TokenizedExample,
    TokenizerSpec,
)
from self_improvement.neural.lora_trainer import (
    LoRATrainer,
    NeuralFitResult,
    NeuralLearnedWeights,
    TrainingRun,
)
from self_improvement.neural.dataset import (
    DatasetSplitter,
    ExternalCorpus,
    SplitResult,
    TrainHoldoutPair,
)
from self_improvement.neural.benchmark import (
    CapabilitySourceReport,
    NeuralCapabilityBenchmark,
    NeuralCapabilityReport,
)

__all__ = [
    # adapters
    "MockNeuralAdapter",
    "NeuralAdapterConfig",
    "NeuralGenerationStats",
    # pipeline
    "Batch",
    "CheckpointLoadResult",
    "DeterministicTestPipeline",
    "GenerationResult",
    "ModelPipeline",
    "TokenizedExample",
    "TokenizerSpec",
    # lora
    "LoRATrainer",
    "NeuralFitResult",
    "NeuralLearnedWeights",
    "TrainingRun",
    # dataset
    "DatasetSplitter",
    "ExternalCorpus",
    "SplitResult",
    "TrainHoldoutPair",
    # benchmark
    "CapabilitySourceReport",
    "NeuralCapabilityBenchmark",
    "NeuralCapabilityReport",
]
