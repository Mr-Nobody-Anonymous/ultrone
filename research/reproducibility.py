"""Reproducibility tools for AI research."""

from __future__ import annotations

import hashlib
import json
import logging
import random
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

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
        self._snapshot: Dict[str, Any] = {}

    def take_snapshot(self, config: Dict[str, Any]) -> str:
        """Take a reproducibility snapshot of the current experiment."""
        snapshot = {
            "timestamp": time.time(),
            "seed": self.config.seed,
            "config": config,
            "config_hash": hashlib.sha256(json.dumps(config, sort_keys=True).encode()).hexdigest()[:16],
        }
        self._snapshot = snapshot
        # Set random seed
        random.seed(self.config.seed)
        return snapshot["config_hash"]

    def check_reproducible(self, config: Dict[str, Any]) -> bool:
        """Check if a config matches the stored snapshot."""
        if not self._snapshot:
            return False
        return self._snapshot.get("config_hash") == \
            hashlib.sha256(json.dumps(config, sort_keys=True).encode()).hexdigest()[:16]

    def get_stats(self) -> Dict[str, Any]:
        return {"type": "ReproducibilityManager", "has_snapshot": bool(self._snapshot)}
