# Copyright (c) Ultrone Contributors. All rights reserved.
"""Sensor registry for multi-modal sensor management.

Registers sensor descriptors with per-sensor quality characteristics
(timestamp, covariance, confidence, latency, precision, reliability,
uncertainty) and provides typed protocol interfaces for sensor adapters.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Protocol, Sequence, Tuple, TypeVar, runtime_checkable

import numpy as np

from .types import (
    CovarianceMatrix,
    Observation,
    SensorMeasurement,
    SensorStatus,
    SensorType,
    utc_now,
)

__all__ = [
    "SensorDescriptor",
    "SensorSpecification",
    "SensorAdapter",
    "SensorRegistry",
    "SensorRegistrationError",
]


@dataclass
class SensorDescriptor:
    """Identity and quality metadata for a registered sensor."""

    sensor_id: str
    sensor_type: SensorType
    status: SensorStatus = SensorStatus.ONLINE
    timestamp: datetime = field(default_factory=utc_now)
    covariance: Optional[CovarianceMatrix] = None
    confidence: float = 0.9
    latency_seconds: float = 0.0
    precision: float = 0.01
    reliability: float = 1.0
    uncertainty: float = 0.1
    field_of_view: Optional[List[float]] = None
    range: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def update_quality(
        self,
        *,
        status: Optional[SensorStatus] = None,
        confidence: Optional[float] = None,
        latency_seconds: Optional[float] = None,
        precision: Optional[float] = None,
        reliability: Optional[float] = None,
        uncertainty: Optional[float] = None,
    ) -> None:
        """Update sensor quality characteristics in place."""
        self.timestamp = utc_now()
        if status is not None:
            self.status = status
        if confidence is not None:
            self.confidence = max(0.0, min(1.0, confidence))
        if latency_seconds is not None:
            self.latency_seconds = max(0.0, latency_seconds)
        if precision is not None:
            self.precision = max(0.0, precision)
        if reliability is not None:
            self.reliability = max(0.0, min(1.0, reliability))
        if uncertainty is not None:
            self.uncertainty = max(0.0, uncertainty)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "sensor_id": self.sensor_id,
            "sensor_type": self.sensor_type.value,
            "status": self.status.value,
            "timestamp": self.timestamp.isoformat(),
            "confidence": self.confidence,
            "latency_seconds": self.latency_seconds,
            "precision": self.precision,
            "reliability": self.reliability,
            "uncertainty": self.uncertainty,
        }


@dataclass
class SensorSpecification:
    """Declarative specification used to register a sensor."""

    sensor_id: str
    sensor_type: SensorType
    confidence: float = 0.9
    latency_seconds: float = 0.0
    precision: float = 0.01
    reliability: float = 1.0
    uncertainty: float = 0.1
    field_of_view: Optional[List[float]] = None
    range: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@runtime_checkable
class SensorAdapter(Protocol):
    """Protocol for a sensor adapter that produces observations.

    Implementations wrap a physical or simulated sensor and produce
    :class:`Observation` objects. The adapter is responsible for converting
    raw measurements into the platform's observation format.
    """

    sensor_id: str
    sensor_type: SensorType

    async def read(self) -> Observation: ...

    async def calibrate(self) -> None: ...

    async def shutdown(self) -> None: ...


class SensorRegistrationError(RuntimeError):
    """Raised when a sensor cannot be registered."""


class SensorRegistry:
    """Registry of sensors with quality metadata and adapter lookup.

    Supports:

    * registration of sensor specifications
    * adapter registration for active sensing
    * quality updates and status transitions
    * querying by type, status, or ID
    * covariance estimation from precision/reliability
    """

    def __init__(self) -> None:
        self._descriptors: Dict[str, SensorDescriptor] = {}
        self._adapters: Dict[str, SensorAdapter] = {}

    def register(
        self, spec: SensorSpecification, adapter: Optional[SensorAdapter] = None
    ) -> SensorDescriptor:
        """Register a sensor specification, optionally with an adapter."""
        if spec.sensor_id in self._descriptors:
            raise SensorRegistrationError(
                f"Sensor {spec.sensor_id} is already registered"
            )

        descriptor = SensorDescriptor(
            sensor_id=spec.sensor_id,
            sensor_type=spec.sensor_type,
            confidence=spec.confidence,
            latency_seconds=spec.latency_seconds,
            precision=spec.precision,
            reliability=spec.reliability,
            uncertainty=spec.uncertainty,
            field_of_view=spec.field_of_view,
            range=spec.range,
            metadata=dict(spec.metadata),
        )
        self._descriptors[spec.sensor_id] = descriptor

        if adapter is not None:
            self._adapters[spec.sensor_id] = adapter

        return descriptor

    def register_adapter(self, sensor_id: str, adapter: SensorAdapter) -> None:
        """Attach an adapter to an already-registered sensor."""
        if sensor_id not in self._descriptors:
            raise SensorRegistrationError(
                f"Sensor {sensor_id} must be registered before attaching an adapter"
            )
        self._adapters[sensor_id] = adapter

    def unregister(self, sensor_id: str) -> bool:
        """Remove a sensor and its adapter. Returns True if removed."""
        removed = self._descriptors.pop(sensor_id, None) is not None
        self._adapters.pop(sensor_id, None)
        return removed

    def get(self, sensor_id: str) -> Optional[SensorDescriptor]:
        return self._descriptors.get(sensor_id)

    def get_required(self, sensor_id: str) -> SensorDescriptor:
        descriptor = self.get(sensor_id)
        if descriptor is None:
            raise SensorRegistrationError(f"Unknown sensor: {sensor_id}")
        return descriptor

    def get_adapter(self, sensor_id: str) -> Optional[SensorAdapter]:
        return self._adapters.get(sensor_id)

    def update_quality(
        self,
        sensor_id: str,
        *,
        status: Optional[SensorStatus] = None,
        confidence: Optional[float] = None,
        latency_seconds: Optional[float] = None,
        precision: Optional[float] = None,
        reliability: Optional[float] = None,
        uncertainty: Optional[float] = None,
    ) -> SensorDescriptor:
        descriptor = self.get_required(sensor_id)
        descriptor.update_quality(
            status=status,
            confidence=confidence,
            latency_seconds=latency_seconds,
            precision=precision,
            reliability=reliability,
            uncertainty=uncertainty,
        )
        return descriptor

    def set_status(self, sensor_id: str, status: SensorStatus) -> SensorDescriptor:
        return self.update_quality(sensor_id, status=status)

    def by_type(self, sensor_type: SensorType) -> List[SensorDescriptor]:
        return [
            d for d in self._descriptors.values() if d.sensor_type == sensor_type
        ]

    def by_status(self, status: SensorStatus) -> List[SensorDescriptor]:
        return [d for d in self._descriptors.values() if d.status == status]

    def online_sensors(self) -> List[SensorDescriptor]:
        return self.by_status(SensorStatus.ONLINE)

    def all(self) -> List[SensorDescriptor]:
        return list(self._descriptors.values())

    def sensor_ids(self) -> List[str]:
        return list(self._descriptors.keys())

    def estimate_covariance(self, sensor_id: str, dim: int = 3) -> np.ndarray:
        """Estimate a diagonal covariance from precision and reliability."""
        descriptor = self.get_required(sensor_id)
        variance = descriptor.precision**2 / max(descriptor.reliability, 1e-6)
        return np.eye(dim, dtype=np.float64) * variance

    def effective_confidence(self, sensor_id: str) -> float:
        """Confidence weighted by reliability and status."""
        descriptor = self.get_required(sensor_id)
        if descriptor.status == SensorStatus.OFFLINE:
            return 0.0
        if descriptor.status == SensorStatus.DEGRADED:
            return descriptor.confidence * descriptor.reliability * 0.5
        return descriptor.confidence * descriptor.reliability

    def count(self) -> int:
        return len(self._descriptors)

    def clear(self) -> None:
        self._descriptors.clear()
        self._adapters.clear()