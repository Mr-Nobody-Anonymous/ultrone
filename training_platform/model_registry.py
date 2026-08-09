# Copyright (c) Ultrone Contributors. All rights reserved.
"""Model registry for the training platform.

Tracks trained models, their checkpoints, evaluation results, and
deployment status. Every model gets a version, hash, and provenance.
"""

from __future__ import annotations

import hashlib
import json
import logging
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("Ultrone.TrainingPlatform.ModelRegistry")


@dataclass
class TrainedModel:
    """A trained model in the registry."""

    model_id: str
    version: str = "1.0.0"
    checkpoint_path: str = ""
    hash: str = ""
    metrics: Dict[str, float] = field(default_factory=dict)
    status: str = "trained"  # trained, evaluated, deployed, archived
    created_at: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "model_id": self.model_id,
            "version": self.version,
            "checkpoint_path": self.checkpoint_path,
            "hash": self.hash,
            "metrics": self.metrics,
            "status": self.status,
            "created_at": self.created_at,
            "metadata": self.metadata,
        }


class TrainingModelRegistry:
    """Registry for trained models."""

    def __init__(self, storage_dir: str = "training_platform/model_registry"):
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self._models: Dict[str, TrainedModel] = {}

    def register(
        self,
        model_id: str,
        checkpoint_path: str,
        metrics: Optional[Dict[str, float]] = None,
        version: str = "1.0.0",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> TrainedModel:
        """Register a trained model."""
        record = TrainedModel(
            model_id=model_id,
            version=version,
            checkpoint_path=checkpoint_path,
            metrics=metrics or {},
            metadata=metadata or {},
        )
        record.hash = self._compute_hash(checkpoint_path)
        self._models[model_id] = record
        logger.info("Registered trained model '%s' (version=%s)", model_id, version)
        return record

    def _compute_hash(self, path: str) -> str:
        """Compute a SHA-256 hash of the checkpoint file."""
        p = Path(path)
        if not p.exists():
            return ""
        h = hashlib.sha256()
        with open(p, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                h.update(chunk)
        return h.hexdigest()[:16]

    def get(self, model_id: str) -> Optional[TrainedModel]:
        """Get a model by ID."""
        return self._models.get(model_id)

    def list_models(self) -> List[Dict[str, Any]]:
        """List all registered models."""
        return [m.to_dict() for m in self._models.values()]

    def update_status(self, model_id: str, status: str) -> bool:
        """Update a model's status."""
        model = self._models.get(model_id)
        if model is None:
            return False
        model.status = status
        return True

    def get_stats(self) -> Dict[str, Any]:
        """Return registry statistics."""
        return {
            "type": "TrainingModelRegistry",
            "models": len(self._models),
            "deployed": sum(1 for m in self._models.values() if m.status == "deployed"),
        }