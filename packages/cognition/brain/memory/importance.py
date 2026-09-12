# Copyright (c) Ultrone Contributors. All rights reserved.
"""Importance Scorer — assigns importance scores to memory items.

Combines recency, frequency, and semantic salience to determine which
memories are worth keeping, summarizing, or forgetting.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from .base import MemoryItem

logger = logging.getLogger("Ultrone.Brain.Memory.Importance")


@dataclass
class ImportanceConfig:
    """Configuration for importance scoring."""
    recency_weight: float = 0.4
    frequency_weight: float = 0.3
    salience_weight: float = 0.3
    half_life: float = 3600.0  # seconds for recency decay


class ImportanceScorer:
    """Ranks memory items by importance."""

    def __init__(self, config: Optional[ImportanceConfig] = None):
        self.config = config or ImportanceConfig()
        self._access_counts: Dict[str, int] = {}

    def record_access(self, key: str) -> None:
        """Increment the access count for a memory key."""
        self._access_counts[key] = self._access_counts.get(key, 0) + 1

    def score(self, item: MemoryItem) -> float:
        """Compute a composite importance score in [0, 1]."""
        recency = self._recency_score(item.timestamp)
        frequency = self._frequency_score(item.key)
        salience = item.importance
        return (
            self.config.recency_weight * recency
            + self.config.frequency_weight * frequency
            + self.config.salience_weight * salience
        )

    def _recency_score(self, timestamp: float) -> float:
        age = max(0.0, time.time() - timestamp)
        return 2.0 ** (-age / self.config.half_life)

    def _frequency_score(self, key: str) -> float:
        count = self._access_counts.get(key, 0)
        return min(1.0, count / 10.0)

    def rank(self, items: List[MemoryItem], top_n: Optional[int] = None) -> List[MemoryItem]:
        """Rank items by importance (highest first)."""
        ranked = sorted(items, key=lambda it: self.score(it), reverse=True)
        if top_n is not None:
            return ranked[:top_n]
        return ranked

    def get_stats(self) -> Dict[str, Any]:
        return {
            "type": "ImportanceScorer",
            "tracked_keys": len(self._access_counts),
            "total_accesses": sum(self._access_counts.values()),
        }
