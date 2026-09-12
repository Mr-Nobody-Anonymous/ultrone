# Copyright (c) Ultrone Contributors. All rights reserved.
"""Model Manager — end-to-end model lifecycle: training, evaluation,
fine-tuning (LoRA/PEFT), deployment, and automatic rollback.

Integrates with ``ModelRegistry`` and ``CheckpointManager``.
"""

from __future__ import annotations

import logging
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

from .checkpoint_manager import CheckpointManager
from .registry import ModelEntry, ModelRegistry
from .rollback import ModelRollback

logger = logging.getLogger("Ultrone.Models.Manager")


@dataclass
class TrainingConfig:
    """Configuration for a training run."""
    epochs: int = 10
    learning_rate: float = 1e-3
    batch_size: int = 32
    optimizer: str = "adam"
    seed: int = 42
    early_stopping: bool = True
    patience: int = 3
    metrics: List[str] = field(default_factory=lambda: ["loss", "accuracy"])
    lora: bool = False
    lora_rank: int = 8
    lora_alpha: int = 16
    peft: bool = False


class ModelManager:
    """Manages the full model lifecycle.

    Features
    --------
    - Train / evaluate / predict lifecycle
    - LoRA & PEFT parameter-efficient fine-tuning
    - Automatic checkpointing and best-model selection
    - Registry integration
    - Automatic rollback on performance regression
    """

    def __init__(
        self,
        registry: Optional[ModelRegistry] = None,
        checkpoint_manager: Optional[CheckpointManager] = None,
    ):
        self.registry = registry or ModelRegistry()
        self.checkpoints = checkpoint_manager or CheckpointManager()
        self.rollback = ModelRollback(self.registry)
        self._models: Dict[str, Any] = {}
        self._train_history: Dict[str, List[Dict[str, Any]]] = {}
        self._active_training: Dict[str, bool] = {}

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------
    def register_model(
        self,
        name: str,
        architecture: str,
        framework: str = "pytorch",
        **metadata: Any,
    ) -> ModelEntry:
        """Register a new model and return its entry."""
        entry = ModelEntry(name=name, architecture=architecture, framework=framework, metadata=metadata)
        self.registry.register(entry)
        return entry

    def load(self, model_id: str, model_obj: Any = None) -> Optional[Any]:
        """Load (or attach) a model instance for a registered entry."""
        entry = self.registry.get(model_id)
        if entry is None:
            logger.error("Model not found: %s", model_id)
            return None
        if model_obj is not None:
            self._models[model_id] = model_obj
        self.registry.update_status(model_id, "trained" if model_obj is not None else "registered")
        return self._models.get(model_id)

    # ------------------------------------------------------------------
    # Training
    # ------------------------------------------------------------------
    def train(
        self,
        model_id: str,
        train_fn: Callable[[Any, TrainingConfig], Dict[str, float]],
        config: Optional[TrainingConfig] = None,
    ) -> Dict[str, float]:
        """Run a training loop.

        ``train_fn`` receives the model object and the active config, and
        returns a dict of final metrics.
        """
        entry = self.registry.get(model_id)
        if entry is None:
            raise ValueError(f"Model not found: {model_id}")
        model = self._models.get(model_id)
        if model is None:
            raise ValueError(f"Model instance not loaded: {model_id}")

        config = config or TrainingConfig()
        self.registry.update_status(model_id, "training")
        self._active_training[model_id] = True
        history: List[Dict[str, Any]] = []

        try:
            metrics = train_fn(model, config)
            history.append({"epoch": "final", "metrics": metrics, "timestamp": time.time()})
            self._train_history[model_id] = history

            # Save checkpoint
            ckpt = self.checkpoints.save(
                model_id=model_id,
                epoch=config.epochs,
                step=0,
                metrics=metrics,
                state_dict=model,
            )
            entry.checkpoint_path = ckpt.path
            self.registry.update_metrics(model_id, metrics)
            self.registry.update_status(model_id, "trained")

            # Automatic rollback check
            self._maybe_rollback(model_id, metrics)
            return metrics
        except Exception as e:
            logger.exception("Training failed for %s", model_id)
            self.registry.update_status(model_id, "failed")
            self.rollback.rollback(model_id)
            raise RuntimeError(f"Training failed: {e}") from e
        finally:
            self._active_training[model_id] = False

    def _maybe_rollback(self, model_id: str, metrics: Dict[str, float]) -> None:
        """Automatically rollback if the new metrics regress vs. history."""
        history = self.rollback.get_history(model_id)
        if not history:
            return
        baseline = history[-1].metrics
        if not baseline:
            return
        # Compare primary metric
        for metric in ("accuracy", "reward", "f1", "mcc"):
            if metric in metrics and metric in baseline:
                if metrics[metric] < baseline[metric]:
                    logger.warning(
                        "Performance regression on %s for %s: %.4f < %.4f — rolling back",
                        metric, model_id, metrics[metric], baseline[metric],
                    )
                    self.rollback.rollback(model_id, reason="automatic: metric regression")
                return

    # ------------------------------------------------------------------
    # Fine-tuning
    # ------------------------------------------------------------------
    def fine_tune(
        self,
        model_id: str,
        train_fn: Callable[[Any, TrainingConfig], Dict[str, float]],
        config: Optional[TrainingConfig] = None,
        use_lora: bool = False,
    ) -> Dict[str, float]:
        """Fine-tune a model, optionally using LoRA/PEFT style adapters.

        When ``use_lora`` is enabled, the config is annotated so the train_fn
        can build/apply LoRA adapters around the base model.
        """
        config = config or TrainingConfig()
        if use_lora:
            config.lora = True
            logger.info("LoRA fine-tuning enabled for %s (rank=%d, alpha=%d)", model_id, config.lora_rank, config.lora_alpha)
        return self.train(model_id, train_fn, config)

    def create_lora_adapter(self, model_id: str, rank: int = 8, alpha: int = 16) -> Dict[str, Any]:
        """Create a LoRA adapter descriptor for a model."""
        return {
            "adapter_id": f"L-{uuid.uuid4().hex[:10]}",
            "model_id": model_id,
            "rank": rank,
            "alpha": alpha,
            "created_at": time.time(),
            "status": "created",
        }

    # ------------------------------------------------------------------
    # Evaluation
    # ------------------------------------------------------------------
    def evaluate(self, model_id: str, eval_fn: Callable[[Any], Dict[str, float]]) -> Dict[str, float]:
        """Evaluate a model and store results in the registry."""
        model = self._models.get(model_id)
        if model is None:
            raise ValueError(f"Model instance not loaded: {model_id}")
        metrics = eval_fn(model)
        self.registry.update_metrics(model_id, metrics)
        return metrics

    def predict(self, model_id: str, input_data: Any) -> Any:
        """Run inference for a loaded model (default: try .predict or .forward)."""
        model = self._models.get(model_id)
        if model is None:
            raise ValueError(f"Model instance not loaded: {model_id}")
        if hasattr(model, "predict"):
            return model.predict(input_data)
        if hasattr(model, "forward"):
            return model.forward(input_data)
        return model(input_data)

    # ------------------------------------------------------------------
    # Comparison
    # ------------------------------------------------------------------
    def compare(self, model_id_a: str, model_id_b: str) -> Dict[str, Any]:
        """Compare two registered models."""
        return self.registry.compare(model_id_a, model_id_b)

    # ------------------------------------------------------------------
    # Introspection
    # ------------------------------------------------------------------
    def get_training_history(self, model_id: str) -> List[Dict[str, Any]]:
        """Return training history for a model."""
        return self._train_history.get(model_id, [])

    def get_active_training(self) -> List[str]:
        """Return model IDs currently training."""
        return [mid for mid, active in self._active_training.items() if active]

    def get_stats(self) -> Dict[str, Any]:
        """Return manager statistics."""
        return {
            "type": "ModelManager",
            "loaded_models": len(self._models),
            "active_training": self.get_active_training(),
            "registry": self.registry.get_stats(),
            "checkpoints": self.checkpoints.get_stats(),
            "rollbacks": self.rollback.get_stats(),
        }

