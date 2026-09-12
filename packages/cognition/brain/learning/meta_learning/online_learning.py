"""Online learning algorithms for streaming data adaptation."""

from __future__ import annotations

import logging
import numpy as np
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from .base import BaseMetaLearner, MetaLearningConfig, MetaTask

logger = logging.getLogger("Ultrone.Brain.Learning.MetaLearning.OnlineLearning")


@dataclass
class OnlineConfig(MetaLearningConfig):
    """Configuration for online learning."""
    learning_rate: float = 0.01
    forget_factor: float = 0.95
    regularization: float = 1e-4
    window_size: int = 100


class OnlineLearning(BaseMetaLearner):
    """Online learning with streaming data and concept drift adaptation."""

    def __init__(self, config: Optional[OnlineConfig] = None):
        super().__init__(config or OnlineConfig())
        self._params: Dict[str, np.ndarray] = {
            "weights": np.random.randn(64, 1) * 0.01,
            "bias": np.zeros(1)
        }
        self._buffer: List[Tuple[np.ndarray, np.ndarray]] = []
        self._step = 0

    def meta_fit(self, tasks: List[MetaTask]) -> None:
        """Online learning doesn't use batch meta-training."""
        logger.info("OnlineLearning: meta_fit not used; use partial_fit for streaming data")
        self._is_trained = True

    def adapt(self, task: MetaTask) -> None:
        """Adapt to a new task online."""
        if task.support_inputs.size > 0:
            self.partial_fit(task.support_inputs, task.support_targets)

    def predict(self, inputs: np.ndarray) -> np.ndarray:
        w, b = self._params["weights"], self._params["bias"]
        return np.dot(inputs, w) + b

    def partial_fit(self, x: np.ndarray, y: np.ndarray) -> None:
        """Update the model incrementally with a new data point or batch."""
        self._buffer.append((x, y))
        if len(self._buffer) > self.config.window_size:
            self._buffer.pop(0)

        for xi, yi in self._buffer:
            if xi.ndim == 1:
                xi = xi[:, None]
            if yi.ndim == 0 or yi.ndim == 1 and len(yi) < 2:
                yi = np.array([yi])

            pred = np.dot(xi, self._params["weights"]) + self._params["bias"]
            error = pred - yi[:, None] if yi.ndim == 1 else pred - yi
            grad_w = 2 * np.dot(xi.T, error) / len(xi)
            grad_b = 2 * np.mean(error)

            self._params["weights"] -= self.config.learning_rate * (
                grad_w + self.config.regularization * self._params["weights"]
            )
            self._params["bias"] -= self.config.learning_rate * (
                grad_b + self.config.regularization * self._params["bias"]
            )

        self._step += 1
        self._is_trained = True

    def detect_drift(self, x: np.ndarray, y: np.ndarray, threshold: float = 0.5) -> bool:
        """Detect concept drift based on prediction error."""
        pred = self.predict(x)
        error = float(np.mean((pred - y) ** 2))
        drift_detected = error > threshold
        if drift_detected:
            logger.warning(f"Concept drift detected at step {self._step}: error={error:.4f}")
        return drift_detected

    def reset(self) -> None:
        """Reset the online learner to initial state."""
        self._params = {
            "weights": np.random.randn(64, 1) * 0.01,
            "bias": np.zeros(1)
        }
        self._buffer.clear()
        self._step = 0
        self._is_trained = False

