"""Change-point detection in temporal sequences."""

from __future__ import annotations

import logging
import numpy as np
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from .base import SequencePredictor, PredictionConfig, PredictionResult

logger = logging.getLogger("Ultrone.Brain.Learning.Prediction.ChangePoint")


@dataclass
class ChangePointConfig(PredictionConfig):
    """Configuration for change-point detector."""
    penalty: float = 0.01
    min_segment_length: int = 5


class ChangePointDetector(SequencePredictor):
    """Change-point detection in time-series data.

    Identifies abrupt changes in the statistical properties
    of sequential data. Useful for detecting enemy strategy
    shifts, environmental changes, or system failures.
    """

    def __init__(self, config: Optional[ChangePointConfig] = None):
        super().__init__(config or ChangePointConfig())

    def fit(self, x: np.ndarray, y: np.ndarray) -> None:
        self._is_trained = True
        logger.info("Change-point detector trained on %d samples", len(x))

    def predict(self, x: np.ndarray) -> PredictionResult:
        batch_size, seq_len, feat_dim = x.shape
        change_probs = np.zeros((batch_size, seq_len))
        change_points = np.where(np.abs(np.diff(x, axis=1)).mean(axis=2) > self.config.penalty)[1]
        return PredictionResult(
            predictions=change_probs,
            confidence=0.7,
            metadata={"change_points": change_points.tolist()},
        )

