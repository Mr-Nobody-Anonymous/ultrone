# Copyright (c) Ultrone Contributors. All rights reserved.
"""Benchmark History — persistent tracking of benchmark runs over time.

Stores historical benchmark results (never overwrites previous runs) in a
JSON ledger, enabling the self-improvement loop and report generation to
track improvement over time and identify regressions.
"""

from __future__ import annotations

import json
import logging
import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("Ultrone.Benchmarks.History")


@dataclass
class HistoricalRun:
    """A single recorded historical benchmark run."""

    name: str
    accuracy: float
    num_problems: int
    timestamp: float
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "accuracy": self.accuracy,
            "num_problems": self.num_problems,
            "timestamp": self.timestamp,
            "metadata": self.metadata,
        }

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "HistoricalRun":
        return HistoricalRun(
            name=data["name"],
            accuracy=data["accuracy"],
            num_problems=data.get("num_problems", 0),
            timestamp=data.get("timestamp", 0.0),
            metadata=data.get("metadata", {}),
        )


class BenchmarkHistory:
    """Tracks historical benchmark results in a JSON ledger.

    Parameters
    ----------
    ledger_path
        Path to the JSON ledger file. Defaults to
        ``benchmarks/history.json``.
    """

    def __init__(self, ledger_path: str = "benchmarks/history.json") -> None:
        self.ledger_path = Path(ledger_path)
        self.ledger_path.parent.mkdir(parents=True, exist_ok=True)
        self._runs: List[HistoricalRun] = self._load()

    def _load(self) -> List[HistoricalRun]:
        """Load existing runs from the ledger."""
        if not self.ledger_path.exists():
            return []
        try:
            with open(self.ledger_path, "r", encoding="utf-8") as fh:
                data = json.load(fh)
            return [HistoricalRun.from_dict(r) for r in data]
        except Exception as exc:  # noqa: BLE001
            logger.warning("Failed to load benchmark history: %s", exc)
            return []

    def record(self, name: str, accuracy: float, num_problems: int, **metadata: Any) -> HistoricalRun:
        """Record a new benchmark run (appends, never overwrites)."""
        run = HistoricalRun(
            name=name,
            accuracy=accuracy,
            num_problems=num_problems,
            timestamp=time.time(),
            metadata=metadata,
        )
        self._runs.append(run)
        self._save()
        return run

    def _save(self) -> None:
        """Persist the ledger to disk."""
        with open(self.ledger_path, "w", encoding="utf-8") as fh:
            json.dump([r.to_dict() for r in self._runs], fh, indent=2, default=str)

    def get_runs(self, name: Optional[str] = None) -> List[HistoricalRun]:
        """Return all runs, optionally filtered by benchmark name."""
        if name is None:
            return list(self._runs)
        return [r for r in self._runs if r.name == name]

    def get_latest(self, name: str) -> Optional[HistoricalRun]:
        """Return the most recent run for a benchmark name."""
        runs = self.get_runs(name)
        return runs[-1] if runs else None

    def get_best(self, name: str) -> Optional[HistoricalRun]:
        """Return the best (highest accuracy) run for a benchmark name."""
        runs = self.get_runs(name)
        return max(runs, key=lambda r: r.accuracy) if runs else None

    def get_improvement(self, name: str) -> float:
        """Return the improvement between the first and latest run."""
        runs = self.get_runs(name)
        if len(runs) < 2:
            return 0.0
        return runs[-1].accuracy - runs[0].accuracy

    def get_timeseries(self, name: str) -> tuple[List[float], List[float]]:
        """Return (timestamps, accuracies) for charting a benchmark."""
        runs = self.get_runs(name)
        return [r.timestamp for r in runs], [r.accuracy for r in runs]

    def get_stats(self) -> Dict[str, Any]:
        """Return aggregate stats per benchmark."""
        names = sorted({r.name for r in self._runs})
        return {
            "total_runs": len(self._runs),
            "benchmarks": {
                n: {
                    "runs": len(self.get_runs(n)),
                    "latest": self.get_latest(n).accuracy if self.get_latest(n) else None,
                    "best": self.get_best(n).accuracy if self.get_best(n) else None,
                    "improvement": self.get_improvement(n),
                }
                for n in names
            },
        }
