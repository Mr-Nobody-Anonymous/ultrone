# Copyright (c) Ultrone Contributors. All rights reserved.
"""Trajectory prediction for Level 3 projection.

Predicts future entity trajectories using:

* constant-velocity / constant-acceleration models
* Kalman filter extrapolation
* Monte Carlo simulation with uncertainty
* multi-horizon prediction
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Tuple

import numpy as np

from .types import (
    EntityID,
    EntityState,
    PredictedState,
    TrackedEntity,
    Vector3,
    utc_now,
)

__all__ = [
    "TrajectoryPredictor",
    "TrajectoryPredictorConfig",
    "TrajectoryPrediction",
]


@dataclass
class TrajectoryPrediction:
    """A predicted trajectory for an entity."""

    entity_id: EntityID
    horizons: List[float]
    positions: List[Vector3]
    confidences: List[float]
    method: str
    predicted_at: datetime = field(default_factory=utc_now)


class TrajectoryPredictorConfig:
    """Configuration for the trajectory predictor."""

    def __init__(
        self,
        *,
        horizons: Optional[List[float]] = None,
        process_noise: float = 0.1,
        num_monte_carlo: int = 100,
        use_monte_carlo: bool = False,
    ) -> None:
        self.horizons = horizons or [1.0, 2.0, 5.0, 10.0, 30.0]
        self.process_noise = process_noise
        self.num_monte_carlo = num_monte_carlo
        self.use_monte_carlo = use_monte_carlo


class TrajectoryPredictor:
    """Predicts future entity trajectories."""

    def __init__(self, *, config: Optional[TrajectoryPredictorConfig] = None) -> None:
        self._config = config or TrajectoryPredictorConfig()
        self._predictions: List[TrajectoryPrediction] = []

    def predict(
        self, entity: TrackedEntity, *, horizons: Optional[List[float]] = None
    ) -> TrajectoryPrediction:
        """Predict the trajectory of an entity at multiple horizons."""
        horizons = horizons or self._config.horizons
        positions: List[Vector3] = []
        confidences: List[float] = []

        for horizon in horizons:
            if self._config.use_monte_carlo:
                position, confidence = self._predict_monte_carlo(entity, horizon)
            else:
                position, confidence = self._predict_kinematic(entity, horizon)
            positions.append(position)
            confidences.append(confidence)

        prediction = TrajectoryPrediction(
            entity_id=entity.entity_id,
            horizons=list(horizons),
            positions=positions,
            confidences=confidences,
            method="monte_carlo" if self._config.use_monte_carlo else "kinematic",
        )
        self._predictions.append(prediction)
        return prediction

    def _predict_kinematic(
        self, entity: TrackedEntity, horizon: float
    ) -> Tuple[Vector3, float]:
        """Predict position using constant-acceleration kinematics."""
        pos = entity.state.position.as_array()
        vel = entity.state.velocity.as_array()
        acc = entity.state.acceleration.as_array()

        predicted = pos + vel * horizon + 0.5 * acc * horizon**2

        # Confidence decays with horizon.
        confidence = entity.confidence * np.exp(-self._config.process_noise * horizon)
        return Vector3.from_array(predicted), float(np.clip(confidence, 0.0, 1.0))

    def _predict_monte_carlo(
        self, entity: TrackedEntity, horizon: float
    ) -> Tuple[Vector3, float]:
        """Predict position using Monte Carlo simulation with uncertainty."""
        rng = np.random.default_rng()
        pos = entity.state.position.as_array()
        vel = entity.state.velocity.as_array()
        acc = entity.state.acceleration.as_array()

        # Sample velocity noise.
        vel_noise = rng.normal(0, self._config.process_noise, size=(self._config.num_monte_carlo, 3))
        samples = (
            pos
            + (vel + vel_noise) * horizon
            + 0.5 * acc * horizon**2
        )

        mean = np.mean(samples, axis=0)
        std = np.std(samples, axis=0)
        # Confidence based on spread.
        spread = float(np.linalg.norm(std))
        confidence = entity.confidence * np.exp(-spread * horizon)
        return Vector3.from_array(mean), float(np.clip(confidence, 0.0, 1.0))

    def to_predicted_states(
        self, prediction: TrajectoryPrediction
    ) -> List[PredictedState]:
        """Convert a trajectory prediction to PredictedState objects."""
        states: List[PredictedState] = []
        for horizon, position, confidence in zip(
            prediction.horizons, prediction.positions, prediction.confidences
        ):
            state = EntityState(position=position)
            states.append(
                PredictedState(
                    entity_id=prediction.entity_id,
                    horizon_seconds=horizon,
                    state=state,
                    confidence=confidence,
                    method=prediction.method,
                )
            )
        return states

    def predictions(self, limit: Optional[int] = None) -> List[TrajectoryPrediction]:
        predictions = self._predictions
        if limit is not None:
            predictions = predictions[-limit:]
        return list(predictions)

    def clear(self) -> None:
        self._predictions.clear()