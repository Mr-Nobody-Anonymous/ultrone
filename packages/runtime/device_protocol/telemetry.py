"""ULTRONE Device Interface Standard (UDIS) - State Freshness and Telemetry.

Guarantees temporal provenance, prevents agents from reasoning over stale measurements,
and provides monotonic expiration checks.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass(frozen=True)
class DeviceTelemetryMeasurement:
    """Immutable telemetry measurement carrying complete temporal and epistemic provenance."""
    device_id: str
    channel: str
    value: Any
    timestamp: float = field(default_factory=time.time)
    monotonic_timestamp: float = field(default_factory=time.monotonic)
    sequence_number: int = 0
    source: str = "sensor"
    quality: float = 1.0       # 0.0 (degraded) to 1.0 (optimal)
    confidence: float = 1.0    # Epistemic certainty
    ttl_seconds: float = 5.0   # Freshness horizon
    measurement_id: str = field(default_factory=lambda: f"meas-{uuid.uuid4().hex[:12]}")

    @property
    def valid_until(self) -> float:
        """Monotonic timestamp until which this measurement is valid."""
        return self.monotonic_timestamp + self.ttl_seconds

    def is_fresh(self, current_mono: Optional[float] = None) -> bool:
        """Verify whether measurement is still within its validity horizon."""
        now = time.monotonic() if current_mono is None else current_mono
        return now <= self.valid_until

    def to_dict(self) -> Dict[str, Any]:
        return {
            "measurement_id": self.measurement_id,
            "device_id": self.device_id,
            "channel": self.channel,
            "value": self.value,
            "timestamp": self.timestamp,
            "monotonic_timestamp": self.monotonic_timestamp,
            "sequence_number": self.sequence_number,
            "source": self.source,
            "quality": self.quality,
            "confidence": self.confidence,
            "valid_until": self.valid_until,
            "is_fresh": self.is_fresh(),
        }


class TelemetryStreamBuffer:
    """Buffer managing time-series telemetry streams with staleness detection."""

    def __init__(self, device_id: str, max_history: int = 1000):
        self.device_id = device_id
        self.max_history = max_history
        self._channels: Dict[str, List[DeviceTelemetryMeasurement]] = {}
        self._seq = 0

    def push(
        self,
        channel: str,
        value: Any,
        quality: float = 1.0,
        confidence: float = 1.0,
        ttl_seconds: float = 5.0,
        source: str = "sensor",
    ) -> DeviceTelemetryMeasurement:
        """Record a new telemetry item with automatic monotonic sequence stamping."""
        self._seq += 1
        m = DeviceTelemetryMeasurement(
            device_id=self.device_id,
            channel=channel,
            value=value,
            sequence_number=self._seq,
            source=source,
            quality=quality,
            confidence=confidence,
            ttl_seconds=ttl_seconds,
        )
        if channel not in self._channels:
            self._channels[channel] = []
        buf = self._channels[channel]
        buf.append(m)
        if len(buf) > self.max_history:
            buf.pop(0)
        return m

    def get_latest(self, channel: str, require_fresh: bool = True) -> Optional[DeviceTelemetryMeasurement]:
        """Fetch latest measurement, optionally enforcing freshness."""
        buf = self._channels.get(channel)
        if not buf:
            return None
        latest = buf[-1]
        if require_fresh and not latest.is_fresh():
            return None
        return latest

    def get_all_fresh(self) -> Dict[str, DeviceTelemetryMeasurement]:
        """Returns snapshot of latest fresh values across all channels."""
        now = time.monotonic()
        out = {}
        for ch, buf in self._channels.items():
            if buf and buf[-1].is_fresh(now):
                out[ch] = buf[-1]
        return out


# Standard alias for telemetry measurement frame
TelemetryFrame = DeviceTelemetryMeasurement
