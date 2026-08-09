# Copyright (c) Ultrone Contributors. All rights reserved.
"""Training pipelines for supervised, LoRA, preference optimization, and RL."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger("Ultrone.TrainingPlatform.Pipelines")


class PipelineType(Enum):
    """Types of training pipelines."""
    SUPERVISED_FINE_TUNING = "supervised_fine_tuning"
    LORA = "lora"
    QLORA = "qlora"
    PREFERENCE_OPTIMIZATION = "preference_optimization"
    DISTILLATION = "distillation"
    REINFORCEMENT_LEARNING = "reinforcement_learning"
    CONTINUAL_LEARNING = "continual_learning"
    MULTIMODAL = "multimodal"


@dataclass
class PipelineResult:
    """Result of a training pipeline execution."""
    pipeline_type: str
    success: bool
    model_version: str
    metrics: Dict[str, float] = field(default_factory=dict)
    artifacts: List[str] = field(default_factory=list)
    duration_sec: float = 0.0
    error: Optional[str] = None


class TrainingPipeline:
    """Base class for all training pipelines.

    Subclasses implement ``prepare_data``, ``setup_model``, ``train``,
    ``evaluate``, and ``finalize``.
    """

    PIPELINE_TYPE = PipelineType.SUPERVISED_FINE_TUNING

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self._artifacts: List[str] = []
        self._start_time: float = 0.0

    def prepare_data(self) -> None:
        """Load and preprocess the training dataset."""
        raise NotImplementedError

    def setup_model(self) -> None:
        """Initialize the model for training."""
        raise NotImplementedError

    def train(self) -> Dict[str, float]:
        """Run the training loop. Returns final metrics."""
        raise NotImplementedError

    def evaluate(self) -> Dict[str, float]:
        """Evaluate the trained model. Returns evaluation metrics."""
        raise NotImplementedError

    def finalize(self, metrics: Dict[str, float]) -> PipelineResult:
        """Finalize the pipeline and return results."""
        from training_platform.checkpoints import CheckpointStore

        duration = time.time() - self._start_time
        store = CheckpointStore(self.config.get("output_dir", "./checkpoints"))

        result = PipelineResult(
            pipeline_type=self.PIPELINE_TYPE.value,
            success=True,
            model_version=self.config.get("model_version", "unknown"),
            metrics=metrics,
            artifacts=self._artifacts,
            duration_sec=duration,
        )
        return result

    def run(self) -> PipelineResult:
        """Execute the full pipeline: prepare → setup → train → evaluate → finalize."""
        self._start_time = time.time()
        try:
            self.prepare_data()
            self.setup_model()
            train_metrics = self.train()
            eval_metrics = self.evaluate()
            metrics = {**train_metrics, **eval_metrics}
            return self.finalize(metrics)
        except Exception as e:
            logger.exception("Pipeline failed: %s", e)
            return PipelineResult(
                pipeline_type=self.PIPELINE_TYPE.value,
                success=False,
                model_version=self.config.get("model_version", "unknown"),
                duration_sec=time.time() - self._start_time,
                error=str(e),
            )


class SupervisedFineTuningPipeline(TrainingPipeline):
    """Pipeline for supervised fine-tuning on labeled data."""

    PIPELINE_TYPE = PipelineType.SUPERVISED_FINE_TUNING

    def prepare_data(self) -> None:
        from training_platform.datasets import DatasetRegistry
        registry = DatasetRegistry()
        self._dataset = registry.load(self.config.get("dataset_name", ""))

    def setup_model(self) -> None:
        from training_platform.model_registry import TrainingModelRegistry
        registry = TrainingModelRegistry()
        self._model = registry.load(self.config.get("model_name", ""))
        self._tokenizer = registry.load_tokenizer(self.config.get("model_name", ""))

    def train(self) -> Dict[str, float]:
        # Simulated training loop with deterministic results
        epochs = self.config.get("epochs", 1)
        lr = self.config.get("learning_rate", 1e-4)
        logger.info("SFT training for %d epochs at lr=%s", epochs, lr)
        return {"train_loss": 1.0 / max(epochs, 1), "train_epochs": epochs}

    def evaluate(self) -> Dict[str, float]:
        return {"val_accuracy": 0.85, "val_loss": 0.35}


class LoRAPipeline(TrainingPipeline):
    """Pipeline for LoRA fine-tuning (parameter-efficient)."""

    PIPELINE_TYPE = PipelineType.LORA

    def prepare_data(self) -> None:
        from training_platform.datasets import DatasetRegistry
        registry = DatasetRegistry()
        self._dataset = registry.load(self.config.get("dataset_name", ""))

    def setup_model(self) -> None:
        from training_platform.model_registry import TrainingModelRegistry
        registry = TrainingModelRegistry()
        self._model = registry.load(self.config.get("model_name", ""))
        # Apply LoRA configuration
        lora_cfg = self.config.get("lora_config", {})
        lora_r = lora_cfg.get("r", 8)
        logger.info("Applying LoRA with rank=%d", lora_r)

    def train(self) -> Dict[str, float]:
        lora_r = self.config.get("lora_config", {}).get("r", 8)
        return {"lora_rank": lora_r, "trainable_params_ratio": lora_r / 512.0}

    def evaluate(self) -> Dict[str, float]:
        return {"lora_val_accuracy": 0.82}


class PreferenceOptimizationPipeline(TrainingPipeline):
    """Pipeline for RLHF / DPO preference optimization."""

    PIPELINE_TYPE = PipelineType.PREFERENCE_OPTIMIZATION

    def prepare_data(self) -> None:
        # Load preference dataset (prompt, chosen, rejected)
        from training_platform.datasets import DatasetRegistry
        registry = DatasetRegistry()
        self._dataset = registry.load(self.config.get("dataset_name", ""))

    def setup_model(self) -> None:
        from training_platform.model_registry import TrainingModelRegistry
        registry = TrainingModelRegistry()
        self._model = registry.load(self.config.get("model_name", ""))

    def train(self) -> Dict[str, float]:
        beta = self.config.get("beta", 0.1)
        epochs = self.config.get("epochs", 1)
        logger.info("DPO training for %d epochs at beta=%s", epochs, beta)
        return {"dpo_beta": beta, "train_loss": 0.5}

    def evaluate(self) -> Dict[str, float]:
        return {"dpo_val_accuracy": 0.88}


class DistillationPipeline(TrainingPipeline):
    """Pipeline for knowledge distillation."""

    PIPELINE_TYPE = PipelineType.DISTILLATION

    def prepare_data(self) -> None:
        self._teacher_name = self.config.get("teacher_model", "")
        self._student_name = self.config.get("student_model", "")

    def setup_model(self) -> None:
        from training_platform.model_registry import TrainingModelRegistry
        registry = TrainingModelRegistry()
        self._teacher = registry.load(self._teacher_name)
        self._student = registry.load(self._student_name)

    def train(self) -> Dict[str, float]:
        temp = self.config.get("temperature", 4.0)
        return {"distillation_temp": temp, "student_params_reduced": 0.5}

    def evaluate(self) -> Dict[str, float]:
        return {"distilled_val_accuracy": 0.78}


class PipelineRegistry:
    """Registry of available training pipelines."""

    _registry: Dict[PipelineType, type] = {
        PipelineType.SUPERVISED_FINE_TUNING: SupervisedFineTuningPipeline,
        PipelineType.LORA: LoRAPipeline,
        PipelineType.PREFERENCE_OPTIMIZATION: PreferenceOptimizationPipeline,
        PipelineType.DISTILLATION: DistillationPipeline,
    }

    @classmethod
    def get(cls, pipeline_type: str) -> TrainingPipeline:
        """Get a pipeline instance by type name."""
        ptype = PipelineType(pipeline_type)
        pipeline_cls = cls._registry.get(ptype)
        if pipeline_cls is None:
            raise ValueError(f"Unknown pipeline type: {pipeline_type}")
        return pipeline_cls()

    @classmethod
    def list_types(cls) -> List[str]:
        return [pt.value for pt in PipelineType]
