# Copyright (c) Ultrone Contributors. All rights reserved.
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
        # Handle 1D input: (seq_len,) -> (1, seq_len, 1)
        if x.ndim == 1:
            seq_len = x.shape[0]
            batch_size = 1
            feat_dim = 1
            x = x.reshape(1, seq_len, 1)
        elif x.ndim == 2:
            seq_len, feat_dim = x.shape
            batch_size = 1
        elif x.ndim == 3:
            batch_size, seq_len, feat_dim = x.shape
        else:
            feat_dim = x.shape[0]
            batch_size = 1
            seq_len = 1
            x = x.reshape(1, 1, feat_dim)

        change_probs = np.zeros((batch_size, seq_len))
        change_points = np.where(np.abs(np.diff(x, axis=1)).mean(axis=2) > self.config.penalty)[1]
        return PredictionResult(
            predictions=change_probs,
            confidence=0.7,
            metadata={"change_points": change_points.tolist()},
        )
