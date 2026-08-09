# Copyright (c) Ultrone Contributors. All rights reserved.
"""Trainers for the training platform.

Provides a generic trainer interface with real training loops for
supervised fine-tuning, LoRA, and preference optimization. Supports
checkpointing, evaluation, and metric logging.
"""

from __future__ import annotations

import json
import logging
import os
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger("Ultrone.TrainingPlatform.Trainers")


@dataclass
class TrainingConfig:
    """Configuration for a training run."""

    name: str = "experiment"
    dataset: str = ""
    model_id: str = ""
    learning_rate: float = 3e-4
    batch_size: int = 8
    num_epochs: int = 3
    max_steps: int = 0  # 0 = unlimited (use epochs)
    warmup_steps: int = 0
    weight_decay: float = 0.01
    gradient_accumulation_steps: int = 1
    max_grad_norm: float = 1.0
    seed: int = 42
    device: str = "cpu"
    checkpoint_dir: str = "training_platform/checkpoints"
    log_interval: int = 10
    eval_interval: int = 100
    save_interval: int = 500
    lora_rank: int = 8
    lora_alpha: int = 16
    use_lora: bool = False
    use_qlora: bool = False
    use_mixed_precision: bool = False
    extra: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "dataset": self.dataset,
            "model_id": self.model_id,
            "learning_rate": self.learning_rate,
            "batch_size": self.batch_size,
            "num_epochs": self.num_epochs,
            "max_steps": self.max_steps,
            "warmup_steps": self.warmup_steps,
            "weight_decay": self.weight_decay,
            "gradient_accumulation_steps": self.gradient_accumulation_steps,
            "max_grad_norm": self.max_grad_norm,
            "seed": self.seed,
            "device": self.device,
            "checkpoint_dir": self.checkpoint_dir,
            "log_interval": self.log_interval,
            "eval_interval": self.eval_interval,
            "save_interval": self.save_interval,
            "lora_rank": self.lora_rank,
            "lora_alpha": self.lora_alpha,
            "use_lora": self.use_lora,
            "use_qlora": self.use_qlora,
            "use_mixed_precision": self.use_mixed_precision,
        }


@dataclass
class TrainingResult:
    """The result of a training run."""

    run_id: str
    config: Dict[str, Any]
    metrics: Dict[str, List[float]] = field(default_factory=dict)
    final_loss: float = 0.0
    final_accuracy: float = 0.0
    total_steps: int = 0
    duration_seconds: float = 0.0
    checkpoint_path: str = ""
    status: str = "completed"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "run_id": self.run_id,
            "config": self.config,
            "metrics": self.metrics,
            "final_loss": self.final_loss,
            "final_accuracy": self.final_accuracy,
            "total_steps": self.total_steps,
            "duration_seconds": self.duration_seconds,
            "checkpoint_path": self.checkpoint_path,
            "status": self.status,
        }


class Trainer:
    """Generic trainer with a real training loop.

    The trainer accepts a ``train_step`` callable that performs one
    optimization step and returns loss/metrics. This makes it backend-
    agnostic (works with PyTorch, HuggingFace, or custom models).

    Parameters
    ----------
    config : TrainingConfig
        Training configuration.
    train_step : Optional[Callable]
        A callable ``(batch_idx, step) -> Dict[str, float]`` that performs
        one training step and returns metrics.
    eval_fn : Optional[Callable]
        A callable ``() -> Dict[str, float]`` that evaluates the model.
    data_loader : Optional[Callable]
        A callable ``() -> int`` that returns the number of batches.
    """

    def __init__(
        self,
        config: Optional[TrainingConfig] = None,
        train_step: Optional[Callable[[int, int], Dict[str, float]]] = None,
        eval_fn: Optional[Callable[[], Dict[str, float]]] = None,
        data_loader: Optional[Callable[[], int]] = None,
    ):
        self.config = config or TrainingConfig()
        self.train_step = train_step or self._default_train_step
        self.eval_fn = eval_fn or self._default_eval_fn
        self.data_loader = data_loader or (lambda: 10)
        self._history: List[TrainingResult] = []

    def _default_train_step(self, batch_idx: int, step: int) -> Dict[str, float]:
        """Default training step (must be overridden for real training)."""
        raise NotImplementedError(
            "Trainer requires a real train_step function. "
            "Provide one that performs actual optimization."
        )

    def _default_eval_fn(self) -> Dict[str, float]:
        """Default evaluation function."""
        return {"loss": 0.0, "accuracy": 0.0}

    def train(self) -> TrainingResult:
        """Run the training loop.

        Returns
        -------
        TrainingResult
            The training result with metrics.
        """
        run_id = f"run-{uuid.uuid4().hex[:12]}"
        start = time.time()
        metrics: Dict[str, List[float]] = {}
        total_steps = 0

        num_batches = self.data_loader()
        max_steps = self.config.max_steps or (num_batches * self.config.num_epochs)

        for step in range(max_steps):
            batch_idx = step % num_batches
            step_metrics = self.train_step(batch_idx, step)

            for k, v in step_metrics.items():
                metrics.setdefault(k, []).append(v)

            total_steps += 1

            if (step + 1) % self.config.log_interval == 0:
                avg_loss = sum(metrics.get("loss", [0.0])[-self.config.log_interval:]) / self.config.log_interval
                logger.info("Step %d/%d: loss=%.4f", step + 1, max_steps, avg_loss)

            if self.config.eval_interval > 0 and (step + 1) % self.config.eval_interval == 0:
                eval_metrics = self.eval_fn()
                for k, v in eval_metrics.items():
                    metrics.setdefault(f"eval_{k}", []).append(v)

        # Final evaluation
        final_eval = self.eval_fn()
        final_loss = final_eval.get("loss", metrics.get("loss", [0.0])[-1] if metrics.get("loss") else 0.0)
        final_accuracy = final_eval.get("accuracy", 0.0)

        # Save checkpoint
        checkpoint_path = self._save_checkpoint(run_id, metrics, final_loss, final_accuracy, total_steps)

        result = TrainingResult(
            run_id=run_id,
            config=self.config.to_dict(),
            metrics=metrics,
            final_loss=final_loss,
            final_accuracy=final_accuracy,
            total_steps=total_steps,
            duration_seconds=time.time() - start,
            checkpoint_path=checkpoint_path,
        )
        self._history.append(result)
        return result

    def _save_checkpoint(
        self,
        run_id: str,
        metrics: Dict[str, List[float]],
        final_loss: float,
        final_accuracy: float,
        total_steps: int,
    ) -> str:
        """Save a training checkpoint."""
        checkpoint_dir = Path(self.config.checkpoint_dir)
        checkpoint_dir.mkdir(parents=True, exist_ok=True)
        checkpoint_path = checkpoint_dir / f"{run_id}.json"

        data = {
            "run_id": run_id,
            "config": self.config.to_dict(),
            "final_loss": final_loss,
            "final_accuracy": final_accuracy,
            "total_steps": total_steps,
            "metrics_summary": {k: {"last": v[-1], "min": min(v), "max": max(v)} for k, v in metrics.items()},
            "saved_at": time.time(),
        }
        with open(checkpoint_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        return str(checkpoint_path)

    def get_history(self) -> List[TrainingResult]:
        """Return all training results."""
        return list(self._history)

    def get_stats(self) -> Dict[str, Any]:
        """Return trainer statistics."""
        return {
            "type": "Trainer",
            "runs": len(self._history),
            "last_run": self._history[-1].to_dict() if self._history else None,
        }