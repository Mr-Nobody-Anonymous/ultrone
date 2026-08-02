# Copyright (c) Ultrone Contributors. All rights reserved.
"""Model Registry — central registry for all AI models with versioning."""

from __future__ import annotations

import logging
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger("Ultrone.Models.Registry")


@dataclass
class ModelEntry:
    """A registered model entry."""
    model_id: str = field(default_factory=lambda: f"M-{uuid.uuid4().hex[:12]}")
    name: str = ""
    version: str = "1.0.0"
    architecture: str = ""
    framework: str = "pytorch"
    parameters: Dict[str, Any] = field(default_factory=dict)
    metrics: Dict[str, float] = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)
    status: str = "registered"  # registered, training, trained, deployed, archived
    checkpoint_path: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "model_id": self.model_id, "name": self.name, "version": self.version,
            "architecture": self.architecture, "framework": self.framework,
            "parameters": self.parameters, "metrics": self.metrics, "tags": self.tags,
            "status": self.status, "checkpoint_path": self.checkpoint_path,
            "metadata": self.metadata, "created_at": self.created_at, "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ModelEntry":
        return cls(
            model_id=data.get("model_id", f"M-{uuid.uuid4().hex[:12]}"),
            name=data.get("name", ""), version=data.get("version", "1.0.0"),
            architecture=data.get("architecture", ""), framework=data.get("framework", "pytorch"),
            parameters=data.get("parameters", {}), metrics=data.get("metrics", {}),
            tags=data.get("tags", []), status=data.get("status", "registered"),
            checkpoint_path=data.get("checkpoint_path", ""), metadata=data.get("metadata", {}),
            created_at=data.get("created_at", time.time()), updated_at=data.get("updated_at", time.time()),
        )


class ModelRegistry:
    """Central model registry with versioning and lifecycle management."""

    def __init__(self):
        self._models: Dict[str, ModelEntry] = {}
        self._by_name: Dict[str, List[str]] = {}  # name -> [model_ids]

    def register(self, entry: ModelEntry) -> ModelEntry:
        """Register a new model."""
        self._models[entry.model_id] = entry
        self._by_name.setdefault(entry.name, []).append(entry.model_id)
        logger.info("Model registered: %s v%s (%s)", entry.name, entry.version, entry.model_id)
        return entry

    def get(self, model_id: str) -> Optional[ModelEntry]:
        return self._models.get(model_id)

    def get_by_name(self, name: str) -> List[ModelEntry]:
        ids = self._by_name.get(name, [])
        return [self._models[mid] for mid in ids if mid in self._models]

    def get_latest(self, name: str) -> Optional[ModelEntry]:
        versions = self.get_by_name(name)
        if not versions:
            return None
        return max(versions, key=lambda m: m.updated_at)

    def update_status(self, model_id: str, status: str) -> bool:
        m = self._models.get(model_id)
        if m is None:
            return False
        m.status = status
        m.updated_at = time.time()
        return True

    def update_metrics(self, model_id: str, metrics: Dict[str, float]) -> bool:
        m = self._models.get(model_id)
        if m is None:
            return False
        m.metrics.update(metrics)
        m.updated_at = time.time()
        return True

    def list_models(self, status: Optional[str] = None) -> List[ModelEntry]:
        if status:
            return [m for m in self._models.values() if m.status == status]
        return list(self._models.values())

    def search(self, query: str, limit: int = 20) -> List[ModelEntry]:
        q = query.lower()
        results = [m for m in self._models.values()
                   if q in m.name.lower() or q in m.architecture.lower() or any(q in t.lower() for t in m.tags)]
        return results[:limit]

    def compare(self, model_id_a: str, model_id_b: str) -> Dict[str, Any]:
        """Compare two models by metrics."""
        a = self._models.get(model_id_a)
        b = self._models.get(model_id_b)
        if a is None or b is None:
            return {"error": "Model not found"}
        all_metrics = set(a.metrics.keys()) | set(b.metrics.keys())
        comparison = {}
        for metric in all_metrics:
            va = a.metrics.get(metric)
            vb = b.metrics.get(metric)
            if va is not None and vb is not None:
                comparison[metric] = {"a": va, "b": vb, "diff": vb - va, "improvement": (vb - va) / va if va != 0 else 0}
        return {"model_a": a.to_dict(), "model_b": b.to_dict(), "metrics": comparison}

    def archive(self, model_id: str) -> bool:
        return self.update_status(model_id, "archived")

    def count(self) -> int:
        return len(self._models)

    def get_stats(self) -> Dict[str, Any]:
        statuses: Dict[str, int] = {}
        for m in self._models.values():
            statuses[m.status] = statuses.get(m.status, 0) + 1
        return {"type": "ModelRegistry", "total_models": len(self._models), "by_status": statuses}