# Copyright (c) Ultrone Contributors. All rights reserved.
"""Checkpoint Manager — saves and restores model checkpoints."""

from __future__ import annotations

import logging
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("Ultrone.Models.Checkpoint")


@dataclass
class Checkpoint:
    """A model checkpoint."""
    checkpoint_id: str = field(default_factory=lambda: f"CK-{uuid.uuid4().hex[:12]}")
    model_id: str = ""
    epoch: int = 0
    step: int = 0
    metrics: Dict[str, float] = field(default_factory=dict)
    path: str = ""
    size_mb: float = 0.0
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {k: v for k, v in self.__dict__.items()}


class CheckpointManager:
    """Manages model checkpoints with automatic cleanup."""

    def __init__(self, base_dir: str = "checkpoints", max_keep: int = 5):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.max_keep = max_keep
        self._checkpoints: Dict[str, Checkpoint] = {}
        self._by_model: Dict[str, List[str]] = {}

    def save(self, model_id: str, epoch: int, step: int, metrics: Dict[str, float], state_dict: Any = None) -> Checkpoint:
        """Save a checkpoint."""
        ckpt = Checkpoint(model_id=model_id, epoch=epoch, step=step, metrics=metrics)
        ckpt.path = str(self.base_dir / f"{model_id}_{ckpt.checkpoint_id}.ckpt")
        self._checkpoints[ckpt.checkpoint_id] = ckpt
        self._by_model.setdefault(model_id, []).append(ckpt.checkpoint_id)
        self._cleanup(model_id)
        logger.info("Checkpoint saved: %s (epoch=%d)", ckpt.checkpoint_id, epoch)
        return ckpt

    def load(self, checkpoint_id: str) -> Optional[Checkpoint]:
        return self._checkpoints.get(checkpoint_id)

    def get_best(self, model_id: str, metric: str = "accuracy", maximize: bool = True) -> Optional[Checkpoint]:
        ids = self._by_model.get(model_id, [])
        ckpts = [self._checkpoints[cid] for cid in ids if cid in self._checkpoints]
        if not ckpts:
            return None
        valid = [c for c in ckpts if metric in c.metrics]
        if not valid:
            return None
        return max(valid, key=lambda c: c.metrics[metric]) if maximize else min(valid, key=lambda c: c.metrics[metric])

    def list_checkpoints(self, model_id: Optional[str] = None) -> List[Checkpoint]:
        if model_id:
            ids = self._by_model.get(model_id, [])
            return [self._checkpoints[cid] for cid in ids if cid in self._checkpoints]
        return list(self._checkpoints.values())

    def _cleanup(self, model_id: str) -> None:
        ids = self._by_model.get(model_id, [])
        if len(ids) <= self.max_keep:
            return
        # Remove oldest
        ckpts = sorted([self._checkpoints[cid] for cid in ids if cid in self._checkpoints], key=lambda c: c.created_at)
        for ckpt in ckpts[:len(ids) - self.max_keep]:
            del self._checkpoints[ckpt.checkpoint_id]
            ids.remove(ckpt.checkpoint_id)

    def get_stats(self) -> Dict[str, Any]:
        return {"type": "CheckpointManager", "total_checkpoints": len(self._checkpoints), "models": len(self._by_model)}