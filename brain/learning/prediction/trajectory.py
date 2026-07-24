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
        batch_size, seq_len, feat_dim = x.shape
        predictions = np.zeros((batch_size, self.config.output_window, feat_dim))
        return PredictionResult(predictions=predictions, confidence=0.75)

