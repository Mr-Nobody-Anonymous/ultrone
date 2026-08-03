# Copyright (c) Ultrone Contributors. All rights reserved.
"""Telemetry Collector — collects platform telemetry for the self-improvement loop.

Tracks performance metrics, resource usage, failure rates, and identifies
weaknesses across the research platform.
"""

from __future__ import annotations

import logging
import time
from collections import defaultdict
from typing import Any, Dict, List, Optional

logger = logging.getLogger("Ultrone.SelfImprovement.Telemetry")


class TelemetryCollector:
    """Collects and analyzes platform telemetry data."""

    def __init__(self):
        self._metrics: Dict[str, List[float]] = defaultdict(list)
        self._events: List[Dict[str, Any]] = []
        self._failures: List[Dict[str, Any]] = []
        self._warnings: List[Dict[str, Any]] = []
        self._start_time = time.time()

    def record_metric(self, name: str, value: float, timestamp: Optional[float] = None) -> None:
        """Record a metric value."""
        self._metrics[name].append(value)

    def record_event(self, event_type: str, details: Dict[str, Any] = None) -> None:
        """Record an event."""
        self._events.append(
            {
                "timestamp": time.time(),
                "type": event_type,
                "details": details or {},
            }
        )

    def record_failure(self, component: str, error: str, details: Dict[str, Any] = None) -> None:
        """Record a failure."""
        self._failures.append(
            {
                "timestamp": time.time(),
                "component": component,
                "error": error,
                "details": details or {},
            }
        )

    def record_warning(self, component: str, message: str, details: Dict[str, Any] = None) -> None:
        """Record a warning."""
        self._warnings.append(
            {
                "timestamp": time.time(),
                "component": component,
                "message": message,
                "details": details or {},
            }
        )

    def get_metric_stats(self, name: str) -> Dict[str, Any]:
        """Get statistics for a metric."""
        values = self._metrics.get(name, [])
        if not values:
            return {"count": 0}
        return {
            "count": len(values),
            "min": min(values),
            "max": max(values),
            "mean": sum(values) / len(values),
            "last": values[-1],
        }

    def identify_weaknesses(self) -> List[Dict[str, Any]]:
        """Identify weaknesses based on telemetry data."""
        weaknesses = []

        # High failure rates
        if self._failures:
            by_component: Dict[str, int] = defaultdict(int)
            for f in self._failures:
                by_component[f["component"]] += 1
            for component, count in by_component.items():
                if count >= 3:
                    weaknesses.append(
                        {
                            "type": "high_failure_rate",
                            "component": component,
                            "failures": count,
                            "severity": "high" if count >= 5 else "medium",
                        }
                    )

        # Performance degradation
        for name, values in self._metrics.items():
            if len(values) >= 5:
                recent = values[-3:]
                older = values[:-3]
                if older and sum(recent) / len(recent) > sum(older) / len(older) * 1.2:
                    weaknesses.append(
                        {
                            "type": "performance_degradation",
                            "metric": name,
                            "recent_avg": sum(recent) / len(recent),
                            "older_avg": sum(older) / len(older),
                            "severity": "medium",
                        }
                    )

        # High warning count
        if len(self._warnings) > 10:
            weaknesses.append(
                {
                    "type": "excessive_warnings",
                    "count": len(self._warnings),
                    "severity": "low",
                }
            )

        return weaknesses

    def get_stats(self) -> Dict[str, Any]:
        """Get telemetry statistics."""
        return {
            "type": "TelemetryCollector",
            "uptime_seconds": time.time() - self._start_time,
            "metrics_tracked": len(self._metrics),
            "events_recorded": len(self._events),
            "failures_recorded": len(self._failures),
            "warnings_recorded": len(self._warnings),
            "weaknesses_identified": len(self.identify_weaknesses()),
        }
