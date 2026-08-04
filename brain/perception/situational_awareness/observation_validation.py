# Copyright (c) Ultrone Contributors. All rights reserved.
"""Observation validation for Level 1 perception.

Validates incoming observations for:

* schema correctness
* timestamp sanity (future / stale)
* value range checks
* covariance positive-definiteness
* confidence bounds
* noise / missing observation handling
* sensor status gating
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Sequence, Tuple

import numpy as np

from .types import Observation, SensorStatus, utc_now

__all__ = [
    "ValidationResult",
    "ValidationRule",
    "ObservationValidator",
    "ValidationError",
]


@dataclass
class ValidationResult:
    """Outcome of validating an observation."""

    observation_id: str
    valid: bool
    reason: str = ""
    warnings: List[str] = field(default_factory=list)
    corrected: Optional[Observation] = None


@dataclass
class ValidationRule:
    """A named validation rule with a predicate."""

    name: str
    predicate: Callable[[Observation], Tuple[bool, str]]


class ValidationError(RuntimeError):
    """Raised when a validation rule itself fails."""


class ObservationValidator:
    """Validates observations against built-in and custom rules.

    Built-in rules cover:

    * timestamp sanity (not in the future, not too stale)
    * confidence bounds [0, 1]
    * covariance positive-definiteness
    * value finite-ness
    * sensor status gating (offline sensors rejected)
    * missing / noisy observation flags
    """

    def __init__(
        self,
        *,
        max_future_skew_seconds: float = 5.0,
        max_stale_seconds: float = 60.0,
        reject_offline_sensors: bool = True,
        auto_correct: bool = True,
    ) -> None:
        self._max_future_skew_seconds = max_future_skew_seconds
        self._max_stale_seconds = max_stale_seconds
        self._reject_offline_sensors = reject_offline_sensors
        self._auto_correct = auto_correct
        self._custom_rules: List[ValidationRule] = []
        self._sensor_status: Dict[str, SensorStatus] = {}

    def register_sensor_status(self, sensor_id: str, status: SensorStatus) -> None:
        """Register the current status of a sensor for gating."""
        self._sensor_status[sensor_id] = status

    def add_rule(self, rule: ValidationRule) -> None:
        """Add a custom validation rule."""
        self._custom_rules.append(rule)

    def validate(self, observation: Observation) -> ValidationResult:
        """Validate an observation against all rules."""
        warnings: List[str] = []
        corrected = observation

        # 1. Sensor status gating
        if self._reject_offline_sensors:
            status = self._sensor_status.get(observation.sensor_id, SensorStatus.ONLINE)
            if status == SensorStatus.OFFLINE:
                return ValidationResult(
                    observation_id=observation.observation_id,
                    valid=False,
                    reason=f"Sensor {observation.sensor_id} is offline",
                )

        # 2. Timestamp sanity
        now = utc_now()
        skew = (observation.timestamp - now).total_seconds()
        if skew > self._max_future_skew_seconds:
            return ValidationResult(
                observation_id=observation.observation_id,
                valid=False,
                reason=f"Observation timestamp {skew:.2f}s in the future",
            )
        if skew < -self._max_stale_seconds:
            warnings.append(
                f"Observation is {abs(skew):.2f}s stale; may be outdated"
            )

        # 3. Confidence bounds
        if not 0.0 <= observation.confidence <= 1.0:
            if self._auto_correct:
                corrected = observation.model_copy(
                    update={"confidence": max(0.0, min(1.0, observation.confidence))}
                )
                warnings.append("Confidence clamped to [0, 1]")
            else:
                return ValidationResult(
                    observation_id=observation.observation_id,
                    valid=False,
                    reason=f"Confidence {observation.confidence} out of bounds",
                )

        # 4. Value finite-ness
        value = observation.measurement.value
        if isinstance(value, (list, tuple, np.ndarray)):
            arr = np.asarray(value, dtype=np.float64)
            if not np.all(np.isfinite(arr)):
                return ValidationResult(
                    observation_id=observation.observation_id,
                    valid=False,
                    reason="Measurement contains non-finite values",
                )

        # 5. Covariance positive-definiteness
        if observation.measurement.covariance is not None:
            cov = observation.measurement.covariance.to_array()
            if not np.all(np.isfinite(cov)):
                return ValidationResult(
                    observation_id=observation.observation_id,
                    valid=False,
                    reason="Covariance contains non-finite values",
                )
            try:
                np.linalg.cholesky(cov + np.eye(cov.shape[0]) * 1e-12)
            except np.linalg.LinAlgError:
                if self._auto_correct:
                    corrected = observation.model_copy(
                        update={
                            "measurement": observation.measurement.model_copy(
                                update={
                                    "covariance": None
                                }
                            )
                        }
                    )
                    warnings.append("Covariance not positive-definite; dropped")
                else:
                    return ValidationResult(
                        observation_id=observation.observation_id,
                        valid=False,
                        reason="Covariance is not positive-definite",
                    )

        # 6. Missing / noisy observation handling
        if observation.is_missing:
            warnings.append("Observation flagged as missing")
        if observation.is_noisy:
            warnings.append("Observation flagged as noisy")

        # 7. Custom rules
        for rule in self._custom_rules:
            try:
                ok, reason = rule.predicate(corrected)
            except Exception as exc:  # pragma: no cover - defensive
                raise ValidationError(
                    f"Validation rule {rule.name} raised: {exc}"
                ) from exc
            if not ok:
                return ValidationResult(
                    observation_id=observation.observation_id,
                    valid=False,
                    reason=f"Rule '{rule.name}' failed: {reason}",
                    warnings=warnings,
                )

        return ValidationResult(
            observation_id=observation.observation_id,
            valid=True,
            warnings=warnings,
            corrected=corrected if corrected is not observation else None,
        )

    def validate_batch(
        self, observations: Sequence[Observation]
    ) -> Tuple[List[Observation], List[ValidationResult]]:
        """Validate a batch; returns (valid_observations, all_results)."""
        valid: List[Observation] = []
        results: List[ValidationResult] = []
        for obs in observations:
            result = self.validate(obs)
            results.append(result)
            if result.valid:
                valid.append(result.corrected or obs)
        return valid, results