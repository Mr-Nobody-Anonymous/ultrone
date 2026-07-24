# Copyright (c) Ultrone Contributors. All rights reserved.
"""Episodic memory for storing specific experiences with temporal context."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from .base import BaseMemory, MemoryConfig, MemoryItem

logger = logging.getLogger("Ultrone.Brain.Memory.Episodic")


@dataclass
class EpisodicConfig(MemoryConfig):
    """Configuration for episodic memory."""
    max_episodes: int = 1000


class EpisodicMemory(BaseMemory):
    """Episodic memory stores specific events/experiences with temporal context."""

    def __init__(self, config: Optional[EpisodicConfig] = None):
        super().__init__(config or EpisodicConfig())
        self._episodes: List[MemoryItem] = []

    def store(self, key: str, content: Any, importance: float = 0.5) -> None:
        item = MemoryItem(key=key, content=content, timestamp=time.time(), importance=importance)
        self._items[key] = item
        self._episodes.append(item)
        if len(self._episodes) > self._config.max_episodes:
            self._episodes.pop(0)

    def recall(self, key: str) -> Optional[Any]:
        item = self._items.get(key)
        return item.content if item else None

    def recall_recent(self, n: int = 10) -> List[MemoryItem]:
        return self._episodes[-n:]

    def forget(self, key: str) -> None:
        self._items.pop(key, None)
        self._episodes = [e for e in self._episodes if e.key != key]