"""Continual/lifelong learning with catastrophic forgetting prevention."""

from __future__ import annotations

import logging
import numpy as np
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from .base import BaseMetaLearner, MetaLearningConfig, MetaTask

logger = logging.getLogger("Ultrone.Brain.Learning.MetaLearning.ContinualLearning")


@dataclass
class ContinualConfig(MetaLearningConfig):
    """Configuration for continual learning."""
    elastic_weight_consolidation: float = 0.5
    memory_size: int = 200
    replay_batch_size: int = 32
    stability_factor: float = 0.3


class ContinualLearning(BaseMetaLearner):
    """Continual learning with EWC (Elastic Weight Consolidation) and replay."""

    def __init__(self, config: Optional[ContinualConfig] = None):
        super().__init__(config or ContinualConfig())
        self._params: Dict[str, np.ndarray] = {
            "weights": np.random.randn(64, 1) * 0.01,
            "bias": np.zeros(1)
        }
        self._fisher_matrix: Dict[str, np.ndarray] = {
            "weights": np.ones((64, 1)),
            "bias": np.ones(1)
        }
        self._optimal_params: Dict[str, np.ndarray] = {
            k: v.copy() for k, v in self._params.items()
        }
        self._memory: List[MetaTask] = []

    def meta_fit(self, tasks: List[MetaTask]) -> None:
        """Train on a sequence of tasks without forgetting."""
        for task in tasks:
            self._train_on_task(task)
            self._update_fisher(task)
            self._store_in_memory(task)

        self._is_trained = True

    def adapt(self, task: MetaTask) -> None:
        """Adapt to a new task while retaining previous knowledge."""
        self._train_on_task(task)
        self._update_fisher(task)
        self._store_in_memory(task)

    def predict(self, inputs: np.ndarray) -> np.ndarray:
        w, b = self._params["weights"], self._params["bias"]
        return np.dot(inputs, w) + b

    def _train_on_task(self, task: MetaTask) -> None:
        """Train on a task with EWC regularization."""
        x, y = task.support_inputs, task.support_targets
        if x.size == 0 or y.size == 0:
            return

        for _ in range(self.config.num_inner_steps):
            pred = np.dot(x, self._params["weights"]) + self._params["bias"]
            task_loss = np.mean((pred - y[:, None] if y.ndim == 1 else pred - y) ** 2)

            # EWC regularization
            ewc_loss = 0.0
            for key in self._params:
                diff = self._params[key] - self._optimal_params[key]
                ewc_loss += np.sum(self._fisher_matrix[key] * diff ** 2)

            total_loss = task_loss + self.config.elastic_weight_consolidation * ewc_loss

            error = pred - y[:, None] if y.ndim == 1 else pred - y
            grad_w = 2 * np.dot(x.T, error) / len(x) + 2 * self.config.elastic_weight_consolidation * self._fisher_matrix["weights"] * (self._params["weights"] - self._optimal_params["weights"])
            grad_b = 2 * np.mean(error) + 2 * self.config.elastic_weight_consolidation * self._fisher_matrix["bias"] * (self._params["bias"] - self._optimal_params["bias"])

            self._params["weights"] -= self.config.inner_lr * grad_w
            self._params["bias"] -= self.config.inner_lr * grad_b

            # Experience replay
            if self._memory:
                replay_task = np.random.choice(self._memory)
                rx, ry = replay_task.support_inputs, replay_task.support_targets
                if rx.size > 0:
                    rpred = np.dot(rx, self._params["weights"]) + self._params["bias"]
                    rerror = rpred - ry[:, None] if ry.ndim == 1 else rpred - ry
                    rgrad_w = 2 * np.dot(rx.T, rerror) / len(rx)
                    rgrad_b = 2 * np.mean(rerror)
                    self._params["weights"] -= self.config.stability_factor * self.config.inner_lr * rgrad_w
                    self._params["bias"] -= self.config.stability_factor * self.config.inner_lr * rgrad_b

    def _update_fisher(self, task: MetaTask) -> None:
        """Update Fisher information matrix for EWC."""
        x, y = task.support_inputs, task.support_targets
        if x.size == 0 or y.size == 0:
            return

        pred = np.dot(x, self._params["weights"]) + self._params["bias"]
        error = pred - y[:, None] if y.ndim == 1 else pred - y

        self._fisher_matrix["weights"] = np.mean(error ** 2, axis=0)[:, None] * np.eye(x.shape[1] if x.ndim > 1 else 1)[:, :64] if x.ndim > 1 else np.ones_like(self._fisher_matrix["weights"])
        self._fisher_matrix["bias"] = np.ones_like(self._fisher_matrix["bias"])

        self._optimal_params = {k: v.copy() for k, v in self._params.items()}

    def _store_in_memory(self, task: MetaTask) -> None:
        """Store task in replay memory."""
        self._memory.append(task)
        if len(self._memory) > self.config.memory_size:
            self._memory.pop(0)

    def forget(self, fraction: float = 0.1) -> None:
        """Simulate forgetting by adding noise to parameters."""
        for key in self._params:
            noise = np.random.randn(*self._params[key].shape) * fraction
            self._params[key] += noise

