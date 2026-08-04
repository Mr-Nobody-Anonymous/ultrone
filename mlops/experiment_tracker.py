# Copyright (c) Ultrone Contributors. All rights reserved.
"""Experiment Tracker — records experiment runs, parameters, and metrics
(MLflow/W&B-style)."""

from __future__ import annotations

import logging
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger("Ultrone.MLOps.ExperimentTracker")


@dataclass
class RunRecord:
    """A single experiment run."""
    run_id: str = field(default_factory=lambda: f"run-{uuid.uuid4().hex[:8]}")
    name: str = ""
    tags: Dict[str, str] = field(default_factory=dict)
    params: Dict[str, Any] = field(default_factory=dict)
    metrics: Dict[str, float] = field(default_factory=dict)
    status: str = "running"      # running, completed, failed
    created_at: float = field(default_factory=time.time)
    end_time: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "run_id": self.run_id, "name": self.name, "tags": self.tags,
            "params": self.params, "metrics": self.metrics, "status": self.status,
            "created_at": self.created_at, "end_time": self.end_time,
        }


class ExperimentTracker:
    """Tracks experiment runs and their metrics."""

    def __init__(self):
        self._runs: Dict[str, RunRecord] = {}
        self._active_run: Optional[RunRecord] = None

    def start_run(self, name: str = "", tags: Optional[Dict[str, str]] = None,
                  params: Optional[Dict[str, Any]] = None) -> str:
        """Start a new run and return its ID."""
        run = RunRecord(name=name, tags=tags or {}, params=params or {})
        self._runs[run.run_id] = run
        self._active_run = run
        logger.info("Started run %s (%s)", run.run_id, name or "unnamed")
        return run.run_id

    def log_metric(self, key: str, value: float) -> None:
        """Log a metric to the active run."""
        if self._active_run:
            self._active_run.metrics[key] = value

    def log_params(self, params: Dict[str, Any]) -> None:
        """Log parameters to the active run."""
        if self._active_run:
            self._active_run.params.update(params)

    def log_tag(self, key: str, value: str) -> None:
        """Log a tag to the active run."""
        if self._active_run:
            self._active_run.tags[key] = value

    def end_run(self, status: str = "completed") -> None:
        """End the active run."""
        if self._active_run:
            self._active_run.status = status
            self._active_run.end_time = time.time()
            self._active_run = None

    def get_run(self, run_id: str) -> Optional[RunRecord]:
        return self._runs.get(run_id)

    def list_runs(self, status: Optional[str] = None) -> List[RunRecord]:
        if status:
            return [r for r in self._runs.values() if r.status == status]
        return list(self._runs.values())

    def get_best(self, metric: str = "accuracy", maximize: bool = True) -> Optional[RunRecord]:
        """Get the best run by a metric."""
        with_metric = [r for r in self._runs.values() if metric in r.metrics]
        if not with_metric:
            return None
        return max(with_metric, key=lambda r: r.metrics[metric]) if maximize \
            else min(with_metric, key=lambda r: r.metrics[metric])

    def get_stats(self) -> Dict[str, Any]:
        return {
            "type": "ExperimentTracker",
            "total_runs": len(self._runs),
            "active_runs": sum(1 for r in self._runs.values() if r.status == "running"),
        }
