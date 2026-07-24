"""Experiment lifecycle management."""

from __future__ import annotations

import json
import logging
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

logger = logging.getLogger("Ultrone.Research.ExperimentManager")


@dataclass
class ExperimentConfig:
    """Configuration for experiments."""
    name: str = "experiment"
    base_dir: str = "experiments"
    save_checkpoints: bool = True
    log_metrics: bool = True


@dataclass
class ExperimentRun:
    """A single experiment run."""
    run_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    config: Dict[str, Any] = field(default_factory=dict)
    metrics: Dict[str, List[float]] = field(default_factory=dict)
    start_time: float = field(default_factory=time.time)
    end_time: Optional[float] = None
    status: str = "running"  # running, completed, failed


class ExperimentManager:
    """Manages experiment lifecycle: creation, execution, and analysis.

    Features:
    - Unique experiment IDs
    - Configuration versioning
    - Metric logging
    - Checkpoint management
    - Result export
    """

    def __init__(self, config: Optional[ExperimentConfig] = None):
        self.config = config or ExperimentConfig()
        self._current_run: Optional[ExperimentRun] = None
        self._runs: List[ExperimentRun] = []

    def create_run(self, run_config: Optional[Dict[str, Any]] = None) -> str:
        """Create a new experiment run. Returns run_id."""
        run = ExperimentRun(config=run_config or {})
        self._current_run = run
        self._runs.append(run)
        logger.info("Experiment run created: %s", run.run_id)
        return run.run_id

    def log_metric(self, name: str, value: float, step: Optional[int] = None) -> None:
        """Log a metric for the current run."""
        if self._current_run is None:
            return
        self._current_run.metrics.setdefault(name, []).append(value)

    def complete_run(self, status: str = "completed") -> None:
        """Mark the current run as completed."""
        if self._current_run:
            self._current_run.status = status
            self._current_run.end_time = time.time()

    def get_all_runs(self) -> List[ExperimentRun]:
        return self._runs

    def get_best_run(self, metric: str = "reward", maximize: bool = True) -> Optional[ExperimentRun]:
        """Get the best run based on a metric."""
        best = None
        best_val = float("-inf") if maximize else float("inf")
        for run in self._runs:
            vals = run.metrics.get(metric, [])
            if vals:
                val = max(vals) if maximize else min(vals)
                if (maximize and val > best_val) or (not maximize and val < best_val):
                    best_val = val
                    best = run
        return best

    def get_stats(self) -> Dict[str, Any]:
        return {
            "type": "ExperimentManager",
            "total_runs": len(self._runs),
            "current_run": self._current_run.run_id if self._current_run else None,
        }
