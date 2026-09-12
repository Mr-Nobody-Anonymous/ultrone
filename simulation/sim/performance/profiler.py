"""Performance profiling and benchmarking tools."""

from __future__ import annotations

import logging
import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple

logger = logging.getLogger("Ultrone.Sim.Performance.Profiler")


@dataclass
class ProfilerConfig:
    """Configuration for profiler."""
    enabled: bool = True
    track_memory: bool = False
    history_size: int = 1000


@dataclass
class ProfileEntry:
    """A single profiling measurement."""
    name: str
    duration_ms: float
    timestamp: float = field(default_factory=time.time)


class Profiler:
    """Performance profiler for simulation benchmarking.

    Provides timing instrumentation, memory tracking, and
    statistical summaries for identifying bottlenecks.
    """

    def __init__(self, config: Optional[ProfilerConfig] = None):
        self.config = config or ProfilerConfig()
        self._entries: Dict[str, List[ProfileEntry]] = defaultdict(list)
        self._timers: Dict[str, float] = {}

    def start(self, name: str) -> None:
        """Start timing a named section."""
        self._timers[name] = time.perf_counter()

    def stop(self, name: str) -> float:
        """Stop timing and record duration. Returns duration in ms."""
        if name not in self._timers:
            return 0.0
        duration_ms = (time.perf_counter() - self._timers.pop(name)) * 1000
        entry = ProfileEntry(name=name, duration_ms=duration_ms)
        self._entries[name].append(entry)
        if len(self._entries[name]) > self.config.history_size:
            self._entries[name].pop(0)
        return duration_ms

    def get_summary(self, name: Optional[str] = None) -> Dict[str, Any]:
        """Get statistical summary for a named section or all sections."""
        if name:
            entries = self._entries.get(name, [])
            durations = [e.duration_ms for e in entries]
            return {
                "name": name,
                "count": len(entries),
                "mean_ms": sum(durations) / max(1, len(durations)),
                "min_ms": min(durations) if durations else 0.0,
                "max_ms": max(durations) if durations else 0.0,
                "total_ms": sum(durations),
            }
        return {name: self.get_summary(name) for name in self._entries}

    def reset(self) -> None:
        self._entries.clear()
        self._timers.clear()

    def get_stats(self) -> Dict[str, Any]:
        return {"type": "Profiler", "sections": len(self._entries)}
