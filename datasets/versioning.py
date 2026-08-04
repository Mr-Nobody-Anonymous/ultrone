# Copyright (c) Ultrone Contributors. All rights reserved.
"""Dataset Versioner — semantic versioning and changelog for datasets."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger("Ultrone.Datasets.Versioning")


@dataclass
class DatasetVersion:
    """A dataset version with changelog."""
    version: str = "1.0.0"
    change: str = ""
    num_samples: int = 0
    created_at: float = field(default_factory=time.time)


class DatasetVersioner:
    """Tracks dataset version history."""

    def __init__(self):
        self._history: Dict[str, List[DatasetVersion]] = {}

    def bump(self, dataset_id: str, change: str, num_samples: int = 0,
             level: str = "patch") -> DatasetVersion:
        """Create a new version for a dataset."""
        history = self._history.setdefault(dataset_id, [])
        current = history[-1].version if history else "1.0.0"
        new_version = self._bump_version(current, level)
        version = DatasetVersion(version=new_version, change=change, num_samples=num_samples)
        history.append(version)
        logger.info("Dataset %s bumped to %s (%s)", dataset_id, new_version, change)
        return version

    def get_history(self, dataset_id: str) -> List[DatasetVersion]:
        """Return the version history for a dataset."""
        return self._history.get(dataset_id, [])

    def get_latest(self, dataset_id: str) -> Optional[DatasetVersion]:
        history = self._history.get(dataset_id, [])
        return history[-1] if history else None

    @staticmethod
    def _bump_version(version: str, level: str) -> str:
        parts = [int(p) for p in version.split(".")]
        if level == "major":
            parts[0] += 1
            parts[1] = 0
            parts[2] = 0
        elif level == "minor":
            parts[1] += 1
            parts[2] = 0
        else:
            parts[2] += 1
        return ".".join(str(p) for p in parts)

    def get_stats(self) -> Dict[str, Any]:
        return {
            "type": "DatasetVersioner",
            "datasets_tracked": len(self._history),
            "total_versions": sum(len(v) for v in self._history.values()),
        }
