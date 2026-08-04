# Copyright (c) Ultrone Contributors. All rights reserved.
"""Model Rollback — automatic rollback to a previous stable model version
when a new model demonstrates performance regression.

Works with ``ModelRegistry`` to snapshot metrics and restore prior states.
"""

from __future__ import annotations

import logging
import time
import uuid
from typing import Any, Dict, List, Optional

from .registry import ModelRegistry

logger = logging.getLogger("Ultrone.Models.Rollback")


class ModelRollback:
    """Manages model version rollback with metric history."""

    def __init__(self, registry: Optional[ModelRegistry] = None):
        self.registry = registry or ModelRegistry()
        self._history: Dict[str, List[Dict[str, Any]]] = {}
        self._rollbacks: List[Dict[str, Any]] = []

    def snapshot(self, model_id: str, metrics: Optional[Dict[str, float]] = None) -> Dict[str, Any]:
        """Record a stable snapshot of a model's metrics."""
        entry = self.registry.get(model_id)
        metrics = metrics or (entry.metrics if entry else {})
        snapshot = {
            "snapshot_id": f"S-{uuid.uuid4().hex[:10]}",
            "model_id": model_id,
            "metrics": dict(metrics),
            "timestamp": time.time(),
        }
        self._history.setdefault(model_id, []).append(snapshot)
        logger.info("Snapshot recorded for %s", model_id)
        return snapshot

    def get_history(self, model_id: str) -> List[Dict[str, Any]]:
        """Return metric history for a model."""
        return self._history.get(model_id, [])

    def has_regression(self, model_id: str, new_metrics: Dict[str, float],
                       metric: str = "accuracy", threshold: float = 0.0) -> bool:
        """Return True if the new metrics regress vs. the last stable snapshot."""
        history = self._history.get(model_id, [])
        if not history:
            return False
        baseline = history[-1].get("metrics", {})
        if metric not in baseline or metric not in new_metrics:
            return False
        return new_metrics[metric] < baseline[metric] - threshold

    def rollback(self, model_id: str, reason: str = "manual") -> Optional[Dict[str, Any]]:
        """Roll a model back to its last stable snapshot.

        Returns the rollback record, or None if there is no history.
        """
        history = self._history.get(model_id, [])
        if not history:
            logger.warning("No rollback history for %s", model_id)
            return None

        target = history[-1]
        # Restore entry metrics in the registry
        entry = self.registry.get(model_id)
        if entry is not None:
            entry.metrics = dict(target["metrics"])
            entry.updated_at = time.time()
            entry.status = "rolled_back"

        record = {
            "rollback_id": f"R-{uuid.uuid4().hex[:10]}",
            "model_id": model_id,
            "reason": reason,
            "restored_snapshot": target["snapshot_id"],
            "restored_metrics": target["metrics"],
            "timestamp": time.time(),
        }
        self._rollbacks.append(record)
        logger.info("Rolled back %s to snapshot %s (%s)", model_id, target["snapshot_id"], reason)
        return record

    def list_rollbacks(self) -> List[Dict[str, Any]]:
        """Return rollback history."""
        return list(self._rollbacks)

    def get_stats(self) -> Dict[str, Any]:
        return {
            "type": "ModelRollback",
            "snapshots": sum(len(v) for v in self._history.values()),
            "rollbacks_performed": len(self._rollbacks),
        }

