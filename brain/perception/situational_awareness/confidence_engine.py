# Copyright (c) Ultrone Contributors. All rights reserved.
"""Confidence estimation and management.

Computes and maintains confidence scores for entities, observations, and
predictions. Supports:

* confidence aggregation across multiple sources
* confidence decay over time
* confidence calibration
* confidence thresholds for decision-making
* confidence-based gating
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np

from .types import Observation, TrackedEntity, utc_now

__all__ = [
    "ConfidenceReport",
    "ConfidenceEngine",
    "ConfidenceConfig",
]


@dataclass
class ConfidenceReport:
    """A confidence assessment for an entity or observation."""

    target_id: str
    confidence: float
    contributing_sources: List[str] = field(default_factory=list)
    source_confidences: List[float] = field(default_factory=list)
    decayed: bool = False
    calibrated: bool = False
    timestamp: datetime = field(default_factory=utc_now)
    metadata: Dict[str, Any] = field(default_factory=dict)


class ConfidenceConfig:
    """Configuration for the confidence engine."""

    def __init__(
        self,
        *,
        decay_rate: float = 0.01,
        decay_enabled: bool = True,
        calibration_enabled: bool = True,
        min_confidence: float = 0.0,
        max_confidence: float = 1.0,
    ) -> None:
        self.decay_rate = decay_rate
        self.decay_enabled = decay_enabled
        self.calibration_enabled = calibration_enabled
        self.min_confidence = min_confidence
        self.max_confidence = max_confidence


class ConfidenceEngine:
    """Computes and manages confidence scores."""

    def __init__(self, *, config: Optional[ConfidenceConfig] = None) -> None:
        self._config = config or ConfidenceConfig()
        self._calibration_map: Dict[float, float] = {}

    def aggregate(
        self,
        confidences: Sequence[float],
        *,
        weights: Optional[Sequence[float]] = None,
        method: str = "weighted_mean",
    ) -> float:
        """Aggregate multiple confidence values into a single score."""
        if not confidences:
            return 0.0
        arr = np.asarray(confidences, dtype=np.float64)
        arr = np.clip(arr, self._config.min_confidence, self._config.max_confidence)

        if method == "max":
            return float(np.max(arr))
        if method == "min":
            return float(np.min(arr))
        if method == "mean":
            return float(np.mean(arr))
        if method == "weighted_mean":
            if weights is None:
                weights = np.ones_like(arr)
            w = np.asarray(weights, dtype=np.float64)
            w = w / w.sum()
            return float(np.sum(w * arr))
        if method == "product":
            return float(np.prod(arr))
        if method == "noisy_or":
            # 1 - prod(1 - c_i)
            return float(1.0 - np.prod(1.0 - arr))
        raise ValueError(f"Unknown aggregation method: {method}")

    def decay(self, confidence: float, elapsed_seconds: float) -> float:
        """Exponentially decay confidence over time."""
        if not self._config.decay_enabled:
            return confidence
        decayed = confidence * np.exp(-self._config.decay_rate * elapsed_seconds)
        return float(np.clip(decayed, self._config.min_confidence, self._config.max_confidence))

    def calibrate(self, confidence: float) -> float:
        """Apply a learned calibration mapping to a confidence score."""
        if not self._config.calibration_enabled or not self._calibration_map:
            return confidence
        # Nearest-neighbor calibration lookup.
        keys = sorted(self._calibration_map.keys())
        nearest = min(keys, key=lambda k: abs(k - confidence))
        return float(np.clip(
            self._calibration_map[nearest],
            self._config.min_confidence,
            self._config.max_confidence,
        ))

    def learn_calibration(
        self, predicted: Sequence[float], actual: Sequence[float]
    ) -> None:
        """Learn a calibration mapping from predicted to actual confidence."""
        if len(predicted) != len(actual):
            raise ValueError("Predicted and actual sequences must have equal length")
        for p, a in zip(predicted, actual):
            self._calibration_map[float(p)] = float(a)

    def assess_observation(self, observation: Observation) -> ConfidenceReport:
        """Assess the confidence of a single observation."""
        confidence = observation.confidence
        sources = [observation.sensor_id]
        source_confidences = [observation.confidence]

        # Adjust for noise and missing flags.
        if observation.is_noisy:
            confidence *= 0.7
        if observation.is_missing:
            confidence *= 0.3

        confidence = self.calibrate(confidence)
        return ConfidenceReport(
            target_id=observation.observation_id,
            confidence=float(np.clip(confidence, 0.0, 1.0)),
            contributing_sources=sources,
            source_confidences=source_confidences,
            calibrated=self._config.calibration_enabled,
        )

    def assess_entity(
        self,
        entity: TrackedEntity,
        *,
        observation_confidences: Optional[Sequence[float]] = None,
        elapsed_seconds: float = 0.0,
    ) -> ConfidenceReport:
        """Assess the overall confidence of a tracked entity."""
        sources: List[str] = []
        source_confidences: List[float] = []

        if observation_confidences:
            source_confidences.extend(observation_confidences)
            sources.extend([f"observation_{i}" for i in range(len(observation_confidences))])

        # Include entity's own confidence as a source.
        source_confidences.append(entity.confidence)
        sources.append("entity_state")

        # Include belief confidence if available.
        if entity.belief is not None:
            belief_conf = 1.0 / (1.0 + entity.belief.uncertainty())
            source_confidences.append(belief_conf)
            sources.append("belief")

        confidence = self.aggregate(source_confidences, method="weighted_mean")
        if elapsed_seconds > 0:
            confidence = self.decay(confidence, elapsed_seconds)
        confidence = self.calibrate(confidence)

        return ConfidenceReport(
            target_id=str(entity.entity_id),
            confidence=float(np.clip(confidence, 0.0, 1.0)),
            contributing_sources=sources,
            source_confidences=source_confidences,
            decayed=elapsed_seconds > 0,
            calibrated=self._config.calibration_enabled,
        )

    def meets_threshold(self, confidence: float, threshold: float) -> bool:
        """Check whether a confidence score meets a decision threshold."""
        return confidence >= threshold

    def gate(
        self, confidence: float, threshold: float
    ) -> Tuple[bool, float]:
        """Gate a decision on confidence; returns (accepted, margin)."""
        margin = confidence - threshold
        return confidence >= threshold, margin