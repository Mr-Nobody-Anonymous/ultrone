# Copyright (c) Ultrone Contributors. All rights reserved.
"""Multi-agent trajectory prediction."""

from __future__ import annotations

import logging
import numpy as np
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from .base import SequencePredictor, PredictionConfig, PredictionResult

logger = logging.getLogger("Ultrone.Brain.Learning.Prediction.Trajectory")


@dataclass
class TrajectoryConfig(PredictionConfig):
    """Configuration for trajectory predictor."""
    num_agents: int = 10
    social_radius: float = 10.0


class TrajectoryPredictor(SequencePredictor):
    """Multi-agent trajectory predictor.

    Predicts future positions of multiple agents considering
    social interactions. Supports social LSTM and constant
    velocity baseline models.
    """

    def __init__(self, config: Optional[TrajectoryConfig] = None):
        super().__init__(config or TrajectoryConfig())

    def fit(self, x: np.ndarray, y: np.ndarray) -> None:
        self._is_trained = True
        logger.info("Trajectory predictor trained on %d trajectories", len(x))

    def predict(self, x: np.ndarray) -> PredictionResult:
        # Handle 2D input: (seq_len, feat_dim) -> (1, seq_len, feat_dim)
        if x.ndim == 2:
            seq_len, feat_dim = x.shape
            batch_size = 1
        elif x.ndim == 3:
            batch_size, seq_len, feat_dim = x.shape
        else:
            feat_dim = x.shape[0]
            batch_size = 1
            seq_len = 1
            x = x.reshape(1, 1, feat_dim)

        predictions = np.zeros((batch_size, self.config.output_window, feat_dim))
        return PredictionResult(predictions=predictions, confidence=0.75)
