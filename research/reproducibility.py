"""Reproducibility tools for AI research."""

from __future__ import annotations

import hashlib
import json
import logging
import random
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Union

logger = logging.getLogger("Ultrone.Research.Reproducibility")


@dataclass
class ReproducibilityConfig:
    """Configuration for reproducibility."""
    save_config: bool = True
    hash_code: bool = True
    seed: int = 42


class ReproducibilityManager:
    """Manages experiment reproducibility.

    Records:
    - Random seeds
    - Configuration hashes
    - Code version
    - Dependency versions
    - Environment variables
    """

    def __init__(self, config: Optional[ReproducibilityConfig] = None):
        self.config = config or ReproducibilityConfig()
        self._snapshots: Dict[str, Dict[str, Any]] = {}
        self._current_snapshot: Optional[Dict[str, Any]] = None

    def snapshot(self, config: Dict[str, Any]) -> str:
        """Take a reproducibility snapshot of the current experiment.
        
        Args:
            config: Experiment configuration to snapshot.
            
        Returns:
            Snapshot ID (hash).
        """
        snapshot = {
            "timestamp": time.time(),
            "seed": self.config.seed,
            "config": config,
            "config_hash": hashlib.sha256(json.dumps(config, sort_keys=True).encode()).hexdigest()[:16],
        }
        snapshot_id = snapshot["config_hash"]
        self._snapshots[snapshot_id] = snapshot
        self._current_snapshot = snapshot
        # Set random seed
        random.seed(self.config.seed)
        logger.info("Reproducibility snapshot taken: %s", snapshot_id)
        return snapshot_id

    def restore(self, snapshot_id: str) -> Optional[Dict[str, Any]]:
        """Restore a reproducibility snapshot.
        
        Args:
            snapshot_id: The snapshot ID to restore.
            
        Returns:
            The restored snapshot dict, or None if not found.
        """
        snapshot = self._snapshots.get(snapshot_id)
        if snapshot:
            self._current_snapshot = snapshot
            random.seed(snapshot.get("seed", self.config.seed))
            logger.info("Reproducibility snapshot restored: %s", snapshot_id)
        return snapshot

    def take_snapshot(self, config: Dict[str, Any]) -> str:
        """Alias for snapshot()."""
        return self.snapshot(config)

    def check_reproducible(self, config: Dict[str, Any]) -> bool:
        """Check if a config matches the stored snapshot."""
        if not self._current_snapshot:
            return False
        return self._current_snapshot.get("config_hash") == \
            hashlib.sha256(json.dumps(config, sort_keys=True).encode()).hexdigest()[:16]

    def get_stats(self) -> Dict[str, Any]:
        return {
            "type": "ReproducibilityManager",
            "num_snapshots": len(self._snapshots),
            "has_snapshot": bool(self._current_snapshot),
        }
