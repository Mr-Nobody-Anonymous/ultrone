# Copyright (c) Ultrone Contributors. All rights reserved.
"""Training Platform — model training, fine-tuning, and evaluation.

Provides dataset registry, validation, preprocessing, training configs,
distributed training, checkpointing, evaluation, benchmarking, model
registry, and deployment pipelines.
"""

from __future__ import annotations

from .datasets import DatasetRegistry, DatasetRecord
from .trainers import Trainer, TrainingConfig, TrainingResult
from .evaluators import Evaluator, EvaluationResult
from .model_registry import TrainingModelRegistry

__all__ = [
    "DatasetRegistry",
    "DatasetRecord",
    "Trainer",
    "TrainingConfig",
    "TrainingResult",
    "Evaluator",
    "EvaluationResult",
    "TrainingModelRegistry",
]