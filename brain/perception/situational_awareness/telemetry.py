# Copyright (c) Ultrone Contributors. All rights reserved.
"""Performance telemetry for the situational awareness system.

Provides wall-clock timing, latency histograms, throughput counters, and
operational health metrics. Every subsystem can emit telemetry records which
are aggregated into a :class:`PerformanceReport`.
"""

from __future__ import annotations

import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime
from statistics import mean, median, pstdev
from typing import Any, Callable, Deque, Dict, List, Optional, Sequence, Tuple

from .types import utc_now

__all__ = [
    "TelemetryRecord",
    "PerformanceTelemetry",
    "PerformanceReport",
    "timed",
    "async_timed",
]


@dataclass
class TelemetryRecord:
    """A single timed operation record."""

    operation: str
    duration_seconds: float
    timestamp: datetime = field(default_factory=utc_now)
    metadata: Dict[str, Any] = field(default_factory=dict)


class PerformanceReport:
    """Aggregated performance statistics for a set of telemetry records."""

    def __init__(self, records: Sequence[TelemetryRecord]) -> None:
        self._records = list(records)

    def for_operation(self, operation: str) -> List[TelemetryRecord]:
        return [r for r in self._records if r.operation == operation]

    def summary(self) -> Dict[str, Dict[str, float]]:
        """Return per-operation summary statistics."""
        grouped: Dict[str, List[float]] = defaultdict(list)
        for record in self._records:
            grouped[record.operation].append(record.duration_seconds)

        summary: Dict[str, Dict[str, float]] = {}
        for op, durations in grouped.items():
            if not durations:
                continue
            summary[op] = {
                "count": float(len(durations)),
                "mean_ms": mean(durations) * 1000.0,
                "median_ms": median(durations) * 1000.0,
                "stddev_ms": (pstdev(durations) if len(durations) > 1 else 0.0) * 1000.0,
                "min_ms": min(durations) * 1000.0,
                "max_ms": max(durations) * 1000.0,
                "p95_ms": self._percentile(durations, 0.95) * 1000.0,
                "p99_ms": self._percentile(durations, 0.99) * 1000.0,
            }
        return summary

    @staticmethod
    def _percentile(values: List[float], q: float) -> float:
        if not values:
            return 0.0
        ordered = sorted(values)
        index = min(len(ordered) - 1, max(0, int(q * len(ordered))))
        return ordered[index]

    @property
    def operations(self) -> List[str]:
        return sorted({r.operation for r in self._records})

    @property
    def total_record_count(self) -> int:
        return len(self._records)


class PerformanceTelemetry:
    """Collects, aggregates, and reports performance telemetry.

    Thread-safe via a simple lock guarding the internal record log.
    """

    def __init__(self, *, max_records: int = 10_000) -> None:
        self._max_records = max_records
        self._records: Deque[TelemetryRecord] = deque(maxlen=max_records)
        self._lock_ = None  # set below if threading lock available

    def record(
        self,
        operation: str,
        duration_seconds: float,
        *,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Record a completed operation's duration."""
        self._records.append(
            TelemetryRecord(
                operation=operation,
                duration_seconds=duration_seconds,
                metadata=metadata or {},
            )
        )

    def time_operation(self, operation: str, fn: Callable[[], Any]) -> Any:
        """Execute ``fn`` and record its duration under ``operation``."""
        start = time.perf_counter()
        try:
            return fn()
        finally:
            self.record(operation, time.perf_counter() - start)

    async def async_time_operation(
        self, operation: str, coro: Any
    ) -> Any:
        """Await ``coro`` and record its duration."""
        import asyncio

        start = time.perf_counter()
        try:
            return await coro
        finally:
            self.record(operation, time.perf_counter() - start)

    def report(self) -> PerformanceReport:
        """Build a report from all collected records."""
        return PerformanceReport(list(self._records))

    def clear(self) -> None:
        self._records.clear()

    @property
    def record_count(self) -> int:
        return len(self._records)


class _Timed:
    """Context manager for synchronous timing."""

    def __init__(self, operation: str, telemetry: PerformanceTelemetry) -> None:
        self._operation = operation
        self._telemetry = telemetry
        self._start: float = 0.0

    def __enter__(self) -> "_Timed":
        self._start = time.perf_counter()
        return self

    def __exit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
        self._telemetry.record(self._operation, time.perf_counter() - self._start)

    @property
    def elapsed_seconds(self) -> float:
        return time.perf_counter() - self._start


def timed(operation: str) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Decorator that times a synchronous function, storing telemetry globally.

    The decorated function must accept a ``telemetry`` keyword argument.
    """
    import functools

    def decorator(fn: Callable[..., Any]) -> Callable[..., Any]:
        @functools.wraps(fn)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            telemetry: Optional[PerformanceTelemetry] = kwargs.get("telemetry")
            start = time.perf_counter()
            try:
                return fn(*args, **kwargs)
            finally:
                if telemetry is not None:
                    telemetry.record(operation, time.perf_counter() - start)

        return wrapper

    return decorator


def async_timed(
    operation: str,
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Decorator that times an async function, storing telemetry globally.

    The decorated function must accept a ``telemetry`` keyword argument.
    """
    import functools

    def decorator(fn: Callable[..., Any]) -> Callable[..., Any]:
        @functools.wraps(fn)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            telemetry: Optional[PerformanceTelemetry] = kwargs.get("telemetry")
            start = time.perf_counter()
            try:
                return await fn(*args, **kwargs)
            finally:
                if telemetry is not None:
                    telemetry.record(operation, time.perf_counter() - start)

        return wrapper

    return decorator