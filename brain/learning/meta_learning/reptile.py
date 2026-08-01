"""Reptile: first-order meta-learning algorithm."""

from __future__ import annotations

import logging
import numpy as np
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from .base import BaseMetaLearner, MetaLearningConfig, MetaTask

logger = logging.getLogger("Ultrone.Brain.Learning.MetaLearning.Reptile")


@dataclass
class ReptileConfig(MetaLearningConfig):
    """Configuration for Reptile."""
    adaptation_steps: int = 5
    meta_lr: float = 0.1


class Reptile(BaseMetaLearner):
    """Reptile: first-order meta-learning by parameter interpolation."""

    def __init__(self, config: Optional[ReptileConfig] = None):
        super().__init__(config or ReptileConfig())
        self._meta_parameters = {
            "weights": np.random.randn(64, 1) * 0.01,
            "bias": np.zeros(1)
        }

    def meta_fit(self, tasks: List[MetaTask]) -> None:
        for iteration in range(self.config.num_meta_iterations):
            for task in np.random.choice(tasks, min(self.config.batch_size, len(tasks)), replace=False):
                adapted = self._adapt_inner(task)

                # Reptile update: move meta-parameters towards adapted parameters
                for key in self._meta_parameters:
                    self._meta_parameters[key] += self.config.meta_lr * (
                        adapted[key] - self._meta_parameters[key]
                    )

            if iteration % 100 == 0:
                logger.info(f"Reptile iteration {iteration}")

        self._is_trained = True

    def adapt(self, task: MetaTask) -> None:
        adapted = self._adapt_inner(task)
        for key in self._meta_parameters:
            self._meta_parameters[key] = adapted[key]

    def predict(self, inputs: np.ndarray) -> np.ndarray:
        w = self._meta_parameters["weights"]
        b = self._meta_parameters["bias"]
        return np.dot(inputs, w) + b

    def _adapt_inner(self, task: MetaTask) -> Dict[str, np.ndarray]:
        adapted = {k: v.copy() for k, v in self._meta_parameters.items()}
        for _ in range(self.config.adaptation_steps):
            pred = np.dot(task.support_inputs, adapted["weights"]) + adapted["bias"]
            error = pred - task.support_targets
            grad_w = 2 * np.dot(task.support_inputs.T, error) / len(task.support_inputs)
            grad_b = 2 * np.mean(error)
            adapted["weights"] -= self.config.inner_lr * grad_w
            adapted["bias"] -= self.config.inner_lr * np.array([grad_b])
        return adapted

