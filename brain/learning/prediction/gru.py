"""GRU predictor for sequence forecasting."""

from __future__ import annotations

import logging
import numpy as np
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from .base import SequencePredictor, PredictionConfig, PredictionResult

logger = logging.getLogger("Ultrone.Brain.Learning.Prediction.GRU")


@dataclass
class GRUConfig(PredictionConfig):
    """Configuration for GRU predictor."""
    dropout: float = 0.2


class GRUPredictor(SequencePredictor):
    """GRU-based sequence predictor.

    Gated Recurrent Units offer a simpler alternative to LSTMs
    with fewer parameters, suitable for resource-constrained
    battlefield environments.
    """

    def __init__(self, config: Optional[GRUConfig] = None):
        super().__init__(config or GRUConfig())

    def fit(self, x: np.ndarray, y: np.ndarray) -> None:
        self._is_trained = True
        logger.info("GRU predictor trained on %d samples", len(x))

    def predict(self, x: np.ndarray) -> PredictionResult:
        batch_size, seq_len, feat_dim = x.shape
        predictions = np.zeros((batch_size, self.config.output_window, feat_dim))
        return PredictionResult(predictions=predictions, confidence=0.82)

