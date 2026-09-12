"""
ULTRONE Metrics Collection (Prometheus-compatible).

Collects and exposes metrics for:
- Cognitive loop latency
- Entity count / update rate
- Model inference latency
- Event bus throughput
- Memory utilization
- Agent task completion rates
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Dict, List


@dataclass
class Counter:
    """A monotonically increasing counter."""
    name: str = ""
    help: str = ""
    value: float = 0.0
    labels: Dict[str, str] = field(default_factory=dict)

    def inc(self, amount: float = 1.0) -> None:
        self.value += amount


@dataclass
class Gauge:
    """A value that can go up and down."""
    name: str = ""
    help: str = ""
    value: float = 0.0
    labels: Dict[str, str] = field(default_factory=dict)

    def set(self, value: float) -> None:
        self.value = value

    def inc(self, amount: float = 1.0) -> None:
        self.value += amount

    def dec(self, amount: float = 1.0) -> None:
        self.value -= amount


@dataclass
class Histogram:
    """Tracks distribution of values."""
    name: str = ""
    help: str = ""
    observations: List[float] = field(default_factory=list)
    labels: Dict[str, str] = field(default_factory=dict)

    def observe(self, value: float) -> None:
        self.observations.append(value)


class MetricsRegistry:
    """Central metrics registry — expose via /metrics endpoint."""

    def __init__(self) -> None:
        self._counters: Dict[str, Counter] = {}
        self._gauges: Dict[str, Gauge] = {}
        self._histograms: Dict[str, Histogram] = {}

    def counter(self, name: str, help: str = "") -> Counter:
        if name not in self._counters:
            self._counters[name] = Counter(name=name, help=help)
        return self._counters[name]

    def gauge(self, name: str, help: str = "") -> Gauge:
        if name not in self._gauges:
            self._gauges[name] = Gauge(name=name, help=help)
        return self._gauges[name]

    def histogram(self, name: str, help: str = "") -> Histogram:
        if name not in self._histograms:
            self._histograms[name] = Histogram(name=name, help=help)
        return self._histograms[name]


__all__ = ["Counter", "Gauge", "Histogram", "MetricsRegistry"]
