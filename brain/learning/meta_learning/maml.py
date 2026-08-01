"""Model-Agnostic Meta-Learning (MAML) implementation."""

from __future__ import annotations

import logging
import numpy as np
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from .base import BaseMetaLearner, MetaLearningConfig, MetaTask

logger = logging.getLogger("Ultrone.Brain.Learning.MetaLearning.MAML")


@dataclass
class MAMLConfig(MetaLearningConfig):
    """Configuration for MAML."""
    first_order: bool = False
    adaptation_steps: int = 5


class MAML(BaseMetaLearner):
    """Model-Agnostic Meta-Learning algorithm."""

    def __init__(self, config: Optional[MAMLConfig] = None):
        super().__init__(config or MAMLConfig())
        self._meta_parameters = {"weights": np.random.randn(64, 1) * 0.01,
                                  "bias": np.zeros(1)}

    def meta_fit(self, tasks: List[MetaTask]) -> None:
        for iteration in range(self.config.num_meta_iterations):
            meta_grads = {"weights": np.zeros_like(self._meta_parameters["weights"]),
                          "bias": np.zeros_like(self._meta_parameters["bias"])}

            for task in tasks[:self.config.batch_size]:
                adapted = self._adapt_inner(task)
                loss = self._compute_loss(adapted, task)
                grads = self._compute_gradients(adapted, task)

                for key in meta_grads:
                    meta_grads[key] += grads.get(key, 0)

            for key in self._meta_parameters:
                self._meta_parameters[key] -= self.config.outer_lr * meta_grads[key] / len(tasks)

            if iteration % 100 == 0:
                logger.info(f"MAML iteration {iteration}: meta-loss = {np.mean([self._compute_loss(self._adapt_inner(t), t) for t in tasks[:5]]):.4f}")

        self._is_trained = True

    def adapt(self, task: MetaTask) -> None:
        self._adapt_inner(task)

    def predict(self, inputs: np.ndarray) -> np.ndarray:
        w = self._meta_parameters["weights"]
        b = self._meta_parameters["bias"]
        return np.dot(inputs, w) + b

    def _adapt_inner(self, task: MetaTask) -> Dict[str, np.ndarray]:
        adapted = {k: v.copy() for k, v in self._meta_parameters.items()}
        for _ in range(self.config.adaptation_steps):
            loss = self._compute_loss(adapted, task)
            grads = self._compute_gradients(adapted, task)
            for key in adapted:
                adapted[key] -= self.config.inner_lr * grads.get(key, 0)
        return adapted

    def _compute_loss(self, params: Dict[str, np.ndarray], task: MetaTask) -> float:
        pred = np.dot(task.support_inputs, params["weights"]) + params["bias"]
        return float(np.mean((pred - task.support_targets) ** 2))

    def _compute_gradients(self, params: Dict[str, np.ndarray], task: MetaTask) -> Dict[str, np.ndarray]:
        pred = np.dot(task.support_inputs, params["weights"]) + params["bias"]
        error = pred - task.support_targets
        grad_w = 2 * np.dot(task.support_inputs.T, error) / len(task.support_inputs)
        grad_b = 2 * np.mean(error)
        return {"weights": grad_w, "bias": np.array([grad_b])}

