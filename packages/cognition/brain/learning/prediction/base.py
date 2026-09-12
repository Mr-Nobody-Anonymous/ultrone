"""Abstract base class for all prediction models."""

from __future__ import annotations

import logging
import numpy as np
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("Ultrone.Brain.Learning.Prediction.Base")


@dataclass
class PredictionConfig:
    """Base configuration for predictors."""
    input_window: int = 64
    output_window: int = 16
    hidden_dim: int = 128
    num_layers: int = 2
    learning_rate: float = 1e-3
    batch_size: int = 32
    num_epochs: int = 100
    device: str = "cpu"


@dataclass
class PredictionResult:
    """Result of a prediction."""
    predictions: np.ndarray
    confidence: float = 0.0
    uncertainty: Optional[np.ndarray] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def mean_prediction(self) -> np.ndarray:
        return np.mean(self.predictions, axis=0) if self.predictions.ndim > 1 else self.predictions


class SequencePredictor(ABC):
    """Abstract interface every predictor must implement."""

    def __init__(self, config: PredictionConfig):
        self.config = config
        self._is_trained = False

    @abstractmethod
    def fit(self, x: np.ndarray, y: np.ndarray) -> None:
        """Train the predictor on historical data."""
        ...

    @abstractmethod
    def predict(self, x: np.ndarray) -> PredictionResult:
        """Generate predictions for input sequence."""
        ...

    def get_stats(self) -> Dict[str, Any]:
        return {
            "type": type(self).__name__,
            "is_trained": self._is_trained,
            "input_window": self.config.input_window,
            "output_window": self.config.output_window,
        }

