# Copyright (c) Ultrone Contributors. All rights reserved.
"""Monitoring Service — tracks model health, latency, and error rates."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger("Ultrone.MLOps.Monitoring")


@dataclass
class MetricSample:
    """A single monitoring sample."""
    timestamp: float = field(default_factory=time.time)
    latency_ms: float = 0.0
    error: bool = False
    throughput: float = 0.0


class MonitoringService:
    """Collects and analyzes model monitoring metrics."""

    def __init__(self, alert_threshold_error_rate: float = 0.05,
                 alert_threshold_latency_ms: float = 500.0):
        self.alert_threshold_error_rate = alert_threshold_error_rate
        self.alert_threshold_latency_ms = alert_threshold_latency_ms
        self._samples: Dict[str, List[MetricSample]] = {}
        self._alerts: List[Dict[str, Any]] = []

    def record(self, model_id: str, latency_ms: float = 0.0, error: bool = False,
               throughput: float = 0.0) -> None:
        """Record a monitoring sample for a model."""
        sample = MetricSample(latency_ms=latency_ms, error=error, throughput=throughput)
        self._samples.setdefault(model_id, []).append(sample)
        self._check_alerts(model_id)

    def _check_alerts(self, model_id: str) -> None:
        samples = self._samples.get(model_id, [])
        recent = samples[-50:]
        if not recent:
            return
        error_rate = sum(1 for s in recent if s.error) / len(recent)
        avg_latency = sum(s.latency_ms for s in recent) / len(recent)
        if error_rate >= self.alert_threshold_error_rate:
            self._alerts.append({
                "model_id": model_id, "type": "high_error_rate",
                "value": error_rate, "timestamp": time.time(),
            })
        if avg_latency >= self.alert_threshold_latency_ms:
            self._alerts.append({
                "model_id": model_id, "type": "high_latency",
                "value": avg_latency, "timestamp": time.time(),
            })

    def get_health(self, model_id: str) -> Dict[str, Any]:
        """Return the health summary for a model."""
        samples = self._samples.get(model_id, [])
        if not samples:
            return {"model_id": model_id, "status": "no_data", "samples": 0}
        recent = samples[-100:]
        error_rate = sum(1 for s in recent if s.error) / len(recent)
        avg_latency = sum(s.latency_ms for s in recent) / len(recent)
        status = "healthy"
        if error_rate >= self.alert_threshold_error_rate:
            status = "degraded"
        if avg_latency >= self.alert_threshold_latency_ms:
            status = "degraded"
        return {
            "model_id": model_id, "status": status, "samples": len(recent),
            "error_rate": error_rate, "avg_latency_ms": avg_latency,
        }

    def get_alerts(self, model_id: Optional[str] = None) -> List[Dict[str, Any]]:
        if model_id:
            return [a for a in self._alerts if a["model_id"] == model_id]
        return list(self._alerts)

    def get_stats(self) -> Dict[str, Any]:
        return {"type": "MonitoringService", "tracked_models": len(self._samples), "alerts": len(self._alerts)}
