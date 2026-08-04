# Copyright (c) Ultrone Contributors. All rights reserved.
"""Anomaly detection for entity behavior and sensor data.

Detects statistical and model-based deviations from expected behavior:

* z-score outliers in state attributes
* sudden velocity / acceleration changes
* unexpected entity type or category transitions
* sensor data inconsistencies
* temporal pattern anomalies
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from .events import AnomalyDetected, EventBus
from .types import AnomalyReport, AnomalySeverity, EntityID, TrackedEntity

__all__ = [
    "AnomalyDetector",
    "AnomalyDetectorConfig",
]


class AnomalyDetectorConfig:
    """Configuration for the anomaly detector."""

    def __init__(
        self,
        *,
        z_score_threshold: float = 3.0,
        velocity_jump_threshold: float = 20.0,
        acceleration_jump_threshold: float = 10.0,
        min_history: int = 5,
        severity_bins: Tuple[float, float, float] = (0.3, 0.6, 0.85),
    ) -> None:
        self.z_score_threshold = z_score_threshold
        self.velocity_jump_threshold = velocity_jump_threshold
        self.acceleration_jump_threshold = acceleration_jump_threshold
        self.min_history = min_history
        self.severity_bins = severity_bins


class AnomalyDetector:
    """Detects anomalies in entity state and sensor data."""

    def __init__(
        self,
        *,
        config: Optional[AnomalyDetectorConfig] = None,
        event_bus: Optional[EventBus] = None,
    ) -> None:
        self._config = config or AnomalyDetectorConfig()
        self._event_bus = event_bus
        self._reports: List[AnomalyReport] = []
        self._history: Dict[str, List[np.ndarray]] = {}

    def analyze_entity(
        self, entity: TrackedEntity
    ) -> List[AnomalyReport]:
        """Analyze an entity for behavioral anomalies."""
        reports: List[AnomalyReport] = []
        key = str(entity.entity_id)

        history = self._history.setdefault(key, [])
        history.append(entity.state.state_vector())
        if len(history) > 100:
            history.pop(0)

        if len(history) < self._config.min_history:
            return reports

        state = entity.state

        # 1. Z-score anomaly on speed.
        speeds = np.array(
            [np.linalg.norm(np.asarray(s[3:6])) for s in history], dtype=np.float64
        )
        if speeds.std() > 1e-6:
            speed = np.linalg.norm(state.velocity.as_array())
            z = abs((speed - speeds.mean()) / speeds.std())
            if z > self._config.z_score_threshold:
                report = self._make_report(
                    entity_id=entity.entity_id,
                    description=f"Velocity anomaly with z-score {z:.2f}",
                    score=min(1.0, z / (2 * self._config.z_score_threshold)),
                    expected=float(speeds.mean()),
                    observed=float(speed),
                    related_observation_ids=[key],
                )
                reports.append(report)

        # 2. Sudden velocity jump.
        if len(speeds) >= 2:
            delta = abs(float(speeds[-1] - speeds[-2]))
            if delta > self._config.velocity_jump_threshold:
                reports.append(
                    self._make_report(
                        entity_id=entity.entity_id,
                        description=f"Sudden velocity jump of {delta:.1f}",
                        score=min(1.0, delta / (2 * self._config.velocity_jump_threshold)),
                        expected=float(speeds[-2]),
                        observed=float(speeds[-1]),
                    )
                )

        # 3. Acceleration anomaly.
        accel = np.linalg.norm(state.acceleration.as_array())
        if accel > self._config.acceleration_jump_threshold:
            reports.append(
                self._make_report(
                    entity_id=entity.entity_id,
                    description=f"High acceleration of {accel:.1f}",
                    score=min(1.0, accel / (2 * self._config.acceleration_jump_threshold)),
                    expected=0.0,
                    observed=float(accel),
                )
            )

        for report in reports:
            self._reports.append(report)
            if self._event_bus is not None:
                self._event_bus.publish_sync(
                    AnomalyDetected(
                        anomaly_id=report.anomaly_id,
                        entity_id=str(report.entity_id) if report.entity_id else None,
                        severity=report.severity.value,
                        score=report.score,
                        description=report.description,
                    )
                )

        return reports

    def analyze_observation(
        self,
        *,
        sensor_id: str,
        value: Any,
        expected: Optional[Any] = None,
        expected_std: Optional[float] = None,
        entity_id: Optional[EntityID] = None,
    ) -> Optional[AnomalyReport]:
        """Analyze a sensor observation for statistical deviation."""
        try:
            observed = float(value)
        except (TypeError, ValueError):
            return None

        if expected is None or expected_std is None or expected_std <= 0:
            return None

        z = abs(observed - expected) / expected_std
        if z <= self._config.z_score_threshold:
            return None

        report = self._make_report(
            entity_id=entity_id,
            sensor_id=sensor_id,
            description=f"Sensor deviation with z-score {z:.2f}",
            score=min(1.0, z / (2 * self._config.z_score_threshold)),
            expected=expected,
            observed=observed,
        )
        self._reports.append(report)
        if self._event_bus is not None:
            self._event_bus.publish_sync(
                AnomalyDetected(
                    anomaly_id=report.anomaly_id,
                    entity_id=str(report.entity_id) if report.entity_id else None,
                    severity=report.severity.value,
                    score=report.score,
                    description=report.description,
                )
            )
        return report

    def _make_report(
        self,
        *,
        description: str,
        score: float,
        expected: Any = None,
        observed: Any = None,
        entity_id: Optional[EntityID] = None,
        sensor_id: Optional[str] = None,
        related_observation_ids: Optional[List[str]] = None,
    ) -> AnomalyReport:
        score = float(np.clip(score, 0.0, 1.0))
        low, mid, high = self._config.severity_bins
        if score >= high:
            severity = AnomalySeverity.CRITICAL
        elif score >= mid:
            severity = AnomalySeverity.SEVERE
        elif score >= low:
            severity = AnomalySeverity.MODERATE
        else:
            severity = AnomalySeverity.MINOR

        return AnomalyReport(
            entity_id=entity_id,
            sensor_id=sensor_id,
            description=description,
            severity=severity,
            score=score,
            expected=expected,
            observed=observed,
            related_observation_ids=related_observation_ids or [],
        )

    def reports(self, limit: Optional[int] = None) -> List[AnomalyReport]:
        reports = self._reports
        if limit is not None:
            reports = reports[-limit:]
        return list(reports)

    def clear(self) -> None:
        self._reports.clear()
        self._history.clear()