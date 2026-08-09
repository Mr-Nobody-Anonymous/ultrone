# Copyright (c) Ultrone Contributors. All rights reserved.
"""Checkpoint storage and versioning for training platform."""

from __future__ import annotations

import hashlib
import json
import logging
import os
import shutil
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger("Ultrone.TrainingPlatform.Checkpoints")


@dataclass
class CheckpointRecord:
    """Metadata for a single checkpoint."""
    checkpoint_id: str
    model_version: str
    step: int
    epoch: int
    path: str
    hash: str
    created_at: float
    metrics: Dict[str, float] = field(default_factory=dict)
    config: Dict[str, Any] = field(default_factory=dict)
    is_best: bool = False
    tags: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "checkpoint_id": self.checkpoint_id,
            "model_version": self.model_version,
            "step": self.step,
            "epoch": self.epoch,
            "path": self.path,
            "hash": self.hash,
            "created_at": self.created_at,
            "metrics": self.metrics,
            "config": self.config,
            "is_best": self.is_best,
            "tags": self.tags,
        }


class CheckpointStore:
    """Stores, versions, and manages model checkpoints.

    Checkpoints are stored in:
    - <output_dir>/checkpoints/step-{N}/ — training checkpoints
    - <output_dir>/checkpoints/best/     — best model
    - <output_dir>/checkpoints/final/   — final model

    Each checkpoint records its hash, metrics, and configuration for
    reproducibility and rollback.
    """

    def __init__(self, output_dir: str = "./checkpoints"):
        self.output_dir = output_dir
        self.checkpoint_dir = os.path.join(output_dir, "checkpoints")
        self.registry_path = os.path.join(self.checkpoint_dir, "registry.json")
        os.makedirs(self.checkpoint_dir, exist_ok=True)
        self._registry: Dict[str, CheckpointRecord] = self._load_registry()

    def _load_registry(self) -> Dict[str, CheckpointRecord]:
        """Load checkpoint registry from disk."""
        if os.path.exists(self.registry_path):
            try:
                with open(self.registry_path, "r") as f:
                    data = json.load(f)
                return {
                    cid: CheckpointRecord(**rec) for cid, rec in data.items()
                }
            except (json.JSONDecodeError, KeyError):
                pass
        return {}

    def _save_registry(self) -> None:
        """Save registry to disk."""
        data = {cid: rec.to_dict() for cid, rec in self._registry.items()}
        with open(self.registry_path, "w") as f:
            json.dump(data, f, indent=2)

    @staticmethod
    def _compute_hash(path: str) -> str:
        """Compute SHA-256 hash of a file."""
        h = hashlib.sha256()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                h.update(chunk)
        return h.hexdigest()[:32]

    def save(
        self,
        state_dict: Dict[str, Any],
        model_version: str,
        step: int,
        epoch: int,
        metrics: Optional[Dict[str, float]] = None,
        config: Optional[Dict[str, Any]] = None,
        tags: Optional[List[str]] = None,
        is_best: bool = False,
    ) -> CheckpointRecord:
        """Save a model checkpoint.

        Parameters
        ----------
        state_dict : Dict[str, Any]
            Model state dictionary.
        model_version : str
            Version identifier for the model.
        step : int
            Training step.
        epoch : int
            Training epoch.
        metrics : Optional[Dict[str, float]]
            Evaluation metrics at this checkpoint.
        config : Optional[Dict[str, Any]]
            Training configuration.
        tags : Optional[List[str]]
            Tags for categorisation (e.g., "lora", "distilled").
        is_best : bool
            Whether this is the best checkpoint so far.
        """
        import torch

        ckpt_id = f"{model_version}-step-{step}-{int(time.time())}"
        ckpt_dir = os.path.join(self.checkpoint_dir, ckpt_id)
        os.makedirs(ckpt_dir, exist_ok=True)
        ckpt_path = os.path.join(ckpt_dir, "pytorch_model.bin")

        torch.save({
            "model_state_dict": state_dict,
            "model_version": model_version,
            "step": step,
            "epoch": epoch,
            "config": config or {},
        }, ckpt_path)

        record = CheckpointRecord(
            checkpoint_id=ckpt_id,
            model_version=model_version,
            step=step,
            epoch=epoch,
            path=ckpt_path,
            hash=self._compute_hash(ckpt_path),
            created_at=time.time(),
            metrics=metrics or {},
            config=config or {},
            is_best=is_best,
            tags=tags or [],
        )
        self._registry[ckpt_id] = record
        self._save_registry()

        # Update best checkpoint symlink
        if is_best:
            best_dir = os.path.join(self.checkpoint_dir, "best")
            if os.path.exists(best_dir):
                shutil.rmtree(best_dir)
            shutil.copytree(ckpt_dir, best_dir)

        logger.info("Saved checkpoint %s at step %d", ckpt_id, step)
        return record

    def load(self, checkpoint_id: str) -> Optional[Dict[str, Any]]:
        """Load a checkpoint by ID.

        Returns the state dict and metadata, or None if not found.
        """
        record = self._registry.get(checkpoint_id)
        if record is None or not os.path.exists(record.path):
            return None

        import torch

        ckpt = torch.load(record.path, map_location="cpu", weights_only=False)
        ckpt["metadata"] = record.to_dict()
        return ckpt

    def get_best(self) -> Optional[CheckpointRecord]:
        """Get the best checkpoint record."""
        best = None
        for rec in self._registry.values():
            if rec.is_best:
                if best is None or rec.metrics.get("accuracy", 0) > best.metrics.get("accuracy", 0):
                    best = rec
        return best

    def list_checkpoints(self) -> List[CheckpointRecord]:
        """List all checkpoints sorted by creation time (newest first)."""
        return sorted(
            self._registry.values(),
            key=lambda r: r.created_at,
            reverse=True,
        )

    def rollback(self, model_version: str) -> Optional[str]:
        """Find the latest checkpoint for a given model version for rollback."""
        matching = [
            rec for rec in self._registry.values()
            if rec.model_version == model_version
        ]
        if not matching:
            return None
        latest = sorted(matching, key=lambda r: r.step, reverse=True)[0]
        return latest.checkpoint_id

    def cleanup(self, keep_best: int = 2, keep_last: int = 2) -> int:
        """Clean up old checkpoints, keeping the best and most recent.

        Returns number of checkpoints removed.
        """
        records = self.list_checkpoints()
        to_remove = []

        # Keep `keep_last` most recent
        for rec in records[keep_last:]:
            if not rec.is_best:
                to_remove.append(rec)

        # Keep `keep_best` best by accuracy
        best_sorted = sorted(
            [r for r in records if r.is_best],
            key=lambda r: r.metrics.get("accuracy", 0),
            reverse=True,
        )
        for rec in best_sorted[keep_best:]:
            to_remove.append(rec)

        removed = 0
        for rec in to_remove:
            if os.path.exists(rec.path):
                shutil.rmtree(os.path.dirname(rec.path), ignore_errors=True)
            del self._registry[rec.checkpoint_id]
            removed += 1

        self._save_registry()
        return removed

    def get_stats(self) -> Dict[str, Any]:
        return {
            "total_checkpoints": len(self._registry),
            "best_checkpoints": sum(1 for r in self._registry.values() if r.is_best),
            "latest_step": max((r.step for r in self._registry.values()), default=0),
        }
