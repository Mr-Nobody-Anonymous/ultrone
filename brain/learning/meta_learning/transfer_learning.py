"""Transfer learning and domain adaptation utilities."""

from __future__ import annotations

import logging
import numpy as np
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple

from .base import BaseMetaLearner, MetaLearningConfig, MetaTask

logger = logging.getLogger("Ultrone.Brain.Learning.MetaLearning.TransferLearning")


@dataclass
class TransferConfig(MetaLearningConfig):
    """Configuration for transfer learning."""
    fine_tune_lr: float = 0.001
    freeze_base: bool = True
    fine_tune_epochs: int = 50
    layer_freeze_pattern: Optional[List[str]] = None


class TransferLearning(BaseMetaLearner):
    """Transfer learning with fine-tuning and feature extraction."""

    def __init__(self, config: Optional[TransferConfig] = None):
        super().__init__(config or TransferConfig())
        self._base_features: Dict[str, np.ndarray] = {}
        self._source_params: Dict[str, np.ndarray] = {}
        self._target_params: Dict[str, np.ndarray] = {}

    def meta_fit(self, tasks: List[MetaTask]) -> None:
        """Pre-train on source tasks."""
        for task in tasks:
            x, y = task.support_inputs, task.support_targets
            if x.size == 0 or y.size == 0:
                continue

            w = np.random.randn(x.shape[1], 1) * 0.01 if x.ndim > 1 else np.random.randn(1, 1) * 0.01
            b = np.zeros(1)

            for _ in range(self.config.fine_tune_epochs):
                pred = np.dot(x, w) + b if x.ndim > 1 else x[:, None] * w + b
                error = pred - y[:, None] if y.ndim == 1 else pred - y
                grad_w = 2 * np.dot(x.T, error) / len(x) if x.ndim > 1 else 2 * np.dot(x[:, None].T, error) / len(x)
                grad_b = 2 * np.mean(error)
                w -= self.config.fine_tune_lr * grad_w
                b -= self.config.fine_tune_lr * grad_b

            self._source_params[task.task_id] = {"weights": w, "bias": b}
            self._base_features[task.task_id] = self._extract_features(x)

        self._is_trained = True
        logger.info(f"TransferLearning: pre-trained on {len(tasks)} source tasks")

    def adapt(self, task: MetaTask) -> None:
        """Fine-tune on a target task."""
        if not self._source_params:
            logger.warning("No source parameters to adapt from")
            return

        # Use average of source parameters as starting point
        avg_w = np.mean([p["weights"] for p in self._source_params.values()], axis=0)
        avg_b = np.mean([p["bias"] for p in self._source_params.values()], axis=0)

        x, y = task.support_inputs, task.support_targets
        if x.size == 0 or y.size == 0:
            self._target_params = {"weights": avg_w, "bias": avg_b}
            return

        w, b = avg_w.copy(), avg_b.copy()
        for _ in range(self.config.fine_tune_epochs):
            pred = np.dot(x, w) + b if x.ndim > 1 else x[:, None] * w + b
            error = pred - y[:, None] if y.ndim == 1 else pred - y
            grad_w = 2 * np.dot(x.T, error) / len(x) if x.ndim > 1 else 2 * np.dot(x[:, None].T, error) / len(x)
            grad_b = 2 * np.mean(error)
            w -= self.config.fine_tune_lr * grad_w
            b -= self.config.fine_tune_lr * grad_b

        self._target_params = {"weights": w, "bias": b}

    def predict(self, inputs: np.ndarray) -> np.ndarray:
        if not self._target_params:
            if not self._source_params:
                return np.zeros((len(inputs), 1))
            avg_w = np.mean([p["weights"] for p in self._source_params.values()], axis=0)
            avg_b = np.mean([p["bias"] for p in self._source_params.values()], axis=0)
            return np.dot(inputs, avg_w) + avg_b

        w, b = self._target_params["weights"], self._target_params["bias"]
        return np.dot(inputs, w) + b

    def freeze_features(self) -> None:
        """Freeze feature extraction layers."""
        self.config.freeze_base = True

    def unfreeze_features(self) -> None:
        """Unfreeze feature extraction layers for fine-tuning."""
        self.config.freeze_base = False

    @staticmethod
    def _extract_features(x: np.ndarray) -> np.ndarray:
        """Extract basic features from input."""
        if x.ndim == 1:
            x = x[:, None]
        return np.hstack([x, x ** 2, np.sin(x), np.cos(x)])

