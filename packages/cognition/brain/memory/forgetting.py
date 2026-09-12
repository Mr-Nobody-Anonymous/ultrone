# Copyright (c) Ultrone Contributors. All rights reserved.
"""Forgetting Engine — implements decay and eviction policies for memory.

Supports least-recently-used (LRU), least-frequently-used (LFU), and
importance-threshold eviction to keep memory bounded and relevant.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from .base import MemoryItem

logger = logging.getLogger("Ultrone.Brain.Memory.Forgetting")


@dataclass
class ForgettingConfig:
    """Configuration for forgetting/eviction."""
    policy: str = "lru"           # lru, lfu, importance
    capacity: int = 1000
    importance_threshold: float = 0.2
    access_counts: Optional[Dict[str, int]] = None


class ForgettingEngine:
    """Performs memory eviction according to a policy."""

    POLICIES = ("lru", "lfu", "importance")

    def __init__(self, config: Optional[ForgettingConfig] = None):
        self.config = config or ForgettingConfig()
        self._evicted: List[Dict[str, Any]] = []

    def evict(self, items: List[MemoryItem]) -> List[MemoryItem]:
        """Evict items (mutates the list) until under capacity.

        Returns the list of evicted items.
        """
        if len(items) <= self.config.capacity:
            return []
        excess = len(items) - self.config.capacity
        evicted = sorted(items, key=lambda it: self._eviction_key(it))[:excess]
        for it in evicted:
            items.remove(it)
            self._evicted.append({
                "key": it.key,
                "policy": self.config.policy,
                "timestamp": time.time(),
            })
        logger.info("Evicted %d items via %s policy", len(evicted), self.config.policy)
        return evicted

    def _eviction_key(self, item: MemoryItem) -> Any:
        """Return a sort key where smallest = evicted first."""
        if self.config.policy == "lfu":
            counts = self.config.access_counts or {}
            return counts.get(item.key, 0)
        if self.config.policy == "importance":
            return item.importance
        # lru: oldest timestamp evicted first
        return item.timestamp

    def forget(self, items: List[MemoryItem], key: str) -> bool:
        """Remove a specific item by key."""
        for it in items:
            if it.key == key:
                items.remove(it)
                return True
        return False

    def get_stats(self) -> Dict[str, Any]:
        return {
            "type": "ForgettingEngine",
            "policy": self.config.policy,
            "evicted_total": len(self._evicted),
        }
