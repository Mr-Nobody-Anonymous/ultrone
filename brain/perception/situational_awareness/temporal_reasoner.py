# Copyright (c) Ultrone Contributors. All rights reserved.
"""Temporal reasoning over entity state histories.

Provides:

* temporal pattern detection (periodicity, trends, anomalies)
* state transition analysis
* temporal correlation between entities
* event sequence analysis
* time-series feature extraction
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import numpy as np

from .types import EntityID, TrackedEntity

__all__ = [
    "TemporalPattern",
    "TemporalCorrelation",
    "TemporalReasoner",
    "TemporalReasonerConfig",
]


@dataclass
class TemporalPattern:
    """A detected temporal pattern in entity state history."""

    pattern_type: str  # "trend", "periodic", "anomaly", "transition"
    entity_id: Optional[EntityID] = None
    attribute: str = ""
    score: float = 0.0
    description: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TemporalCorrelation:
    """Correlation between two entities' temporal state histories."""

    entity_id_a: EntityID
    entity_id_b: EntityID
    correlation: float
    lag: int = 0
    attribute: str = "position"


class TemporalReasonerConfig:
    """Configuration for the temporal reasoner."""

    def __init__(
        self,
        *,
        min_history: int = 5,
        trend_threshold: float = 0.5,
        anomaly_threshold: float = 3.0,
        max_lag: int = 5,
    ) -> None:
        self.min_history = min_history
        self.trend_threshold = trend_threshold
        self.anomaly_threshold = anomaly_threshold
        self.max_lag = max_lag


class TemporalReasoner:
    """Analyzes temporal patterns in entity state histories."""

    def __init__(self, *, config: Optional[TemporalReasonerConfig] = None) -> None:
        self._config = config or TemporalReasonerConfig()
        self._patterns: List[TemporalPattern] = []

    def extract_series(
        self, entity: TrackedEntity, attribute: str = "position"
    ) -> np.ndarray:
        """Extract a time series from an entity's state history."""
        if attribute == "position":
            return np.array(
                [s.position.as_array() for s in entity.history],
                dtype=np.float64,
            )
        if attribute == "velocity":
            return np.array(
                [s.velocity.as_array() for s in entity.history],
                dtype=np.float64,
            )
        if attribute == "speed":
            return np.array(
                [np.linalg.norm(s.velocity.as_array()) for s in entity.history],
                dtype=np.float64,
            )
        if attribute in entity.state.attributes:
            return np.array(
                [s.attributes.get(attribute, 0.0) for s in entity.history],
                dtype=np.float64,
            )
        return np.array([], dtype=np.float64)

    def detect_trend(self, series: np.ndarray) -> Optional[TemporalPattern]:
        """Detect a linear trend in a time series."""
        if series.ndim > 1:
            series = np.linalg.norm(series, axis=1)
        if series.shape[0] < self._config.min_history:
            return None

        x = np.arange(series.shape[0], dtype=np.float64)
        slope, intercept = np.polyfit(x, series, 1)
        predicted = slope * x + intercept
        residuals = series - predicted
        r2 = 1.0 - np.sum(residuals**2) / max(np.sum((series - series.mean())**2), 1e-12)

        if abs(slope) > self._config.trend_threshold and r2 > 0.5:
            direction = "increasing" if slope > 0 else "decreasing"
            return TemporalPattern(
                pattern_type="trend",
                attribute="series",
                score=abs(slope) * r2,
                description=f"{direction} trend with slope {slope:.3f}",
            )
        return None

    def detect_anomalies(self, series: np.ndarray) -> List[TemporalPattern]:
        """Detect statistical anomalies in a time series."""
        if series.ndim > 1:
            series = np.linalg.norm(series, axis=1)
        if series.shape[0] < self._config.min_history:
            return []

        mean = np.mean(series)
        std = np.std(series)
        if std < 1e-12:
            return []

        anomalies: List[TemporalPattern] = []
        z_scores = np.abs((series - mean) / std)
        for i, z in enumerate(z_scores):
            if z > self._config.anomaly_threshold:
                anomalies.append(
                    TemporalPattern(
                        pattern_type="anomaly",
                        attribute="series",
                        score=float(z),
                        description=f"Anomaly at index {i} with z-score {z:.2f}",
                        metadata={"index": i, "value": float(series[i])},
                    )
                )
        return anomalies

    def detect_periodicity(self, series: np.ndarray) -> Optional[TemporalPattern]:
        """Detect periodicity via autocorrelation."""
        if series.ndim > 1:
            series = np.linalg.norm(series, axis=1)
        n = series.shape[0]
        if n < self._config.min_history * 2:
            return None

        centered = series - np.mean(series)
        if np.std(centered) < 1e-12:
            return None

        autocorr = np.correlate(centered, centered, mode="full")[n - 1 :]
        autocorr /= autocorr[0] + 1e-12

        # Find the first significant peak after lag 0.
        for lag in range(2, n // 2):
            if autocorr[lag] > 0.5 and autocorr[lag] > autocorr[lag - 1] and autocorr[lag] > autocorr[lag + 1]:
                return TemporalPattern(
                    pattern_type="periodic",
                    attribute="series",
                    score=float(autocorr[lag]),
                    description=f"Periodicity detected with period {lag}",
                    metadata={"period": lag, "autocorrelation": float(autocorr[lag])},
                )
        return None

    def analyze_entity(
        self, entity: TrackedEntity, attribute: str = "position"
    ) -> List[TemporalPattern]:
        """Analyze an entity's history for temporal patterns."""
        series = self.extract_series(entity, attribute)
        patterns: List[TemporalPattern] = []

        trend = self.detect_trend(series)
        if trend is not None:
            trend.entity_id = entity.entity_id
            patterns.append(trend)

        periodic = self.detect_periodicity(series)
        if periodic is not None:
            periodic.entity_id = entity.entity_id
            patterns.append(periodic)

        anomalies = self.detect_anomalies(series)
        for anomaly in anomalies:
            anomaly.entity_id = entity.entity_id
            patterns.append(anomaly)

        self._patterns.extend(patterns)
        return patterns

    def correlate(
        self,
        entity_a: TrackedEntity,
        entity_b: TrackedEntity,
        attribute: str = "position",
    ) -> Optional[TemporalCorrelation]:
        """Compute cross-correlation between two entities' histories."""
        series_a = self.extract_series(entity_a, attribute)
        series_b = self.extract_series(entity_b, attribute)

        if series_a.ndim > 1:
            series_a = np.linalg.norm(series_a, axis=1)
        if series_b.ndim > 1:
            series_b = np.linalg.norm(series_b, axis=1)

        n = min(series_a.shape[0], series_b.shape[0])
        if n < self._config.min_history:
            return None

        series_a = series_a[:n]
        series_b = series_b[:n]

        best_corr = -1.0
        best_lag = 0
        for lag in range(-self._config.max_lag, self._config.max_lag + 1):
            if lag < 0:
                a = series_a[-lag:]
                b = series_b[:lag]
            elif lag > 0:
                a = series_a[:-lag]
                b = series_b[lag:]
            else:
                a = series_a
                b = series_b

            if a.shape[0] < 2:
                continue
            corr = np.corrcoef(a, b)[0, 1]
            if np.isfinite(corr) and abs(corr) > abs(best_corr):
                best_corr = corr
                best_lag = lag

        if best_corr < 0:
            return None
        return TemporalCorrelation(
            entity_id_a=entity_a.entity_id,
            entity_id_b=entity_b.entity_id,
            correlation=float(best_corr),
            lag=best_lag,
            attribute=attribute,
        )

    def patterns(self) -> List[TemporalPattern]:
        return list(self._patterns)

    def clear(self) -> None:
        self._patterns.clear()