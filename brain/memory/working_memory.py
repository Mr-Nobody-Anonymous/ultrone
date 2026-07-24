# Copyright (c) Ultrone Contributors. All rights reserved.
"""Working memory for short-term, active information."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from .base import BaseMemory, MemoryConfig

logger = logging.getLogger("Ultrone.Brain.Memory.Working")


@dataclass
class WorkingMemoryConfig(MemoryConfig):
    """Configuration for working memory."""
    capacity: int = 100
    decay_rate: float = 0.1


class WorkingMemory(BaseMemory):
    """Short-term working memory with decay and limited capacity."""

    def __init__(self, config: Optional[WorkingMemoryConfig] = None):
        super().__init__(config or WorkingMemoryConfig())
        self._access_times: Dict[str, float] = {}

    def store(self, key: str, content: Any, importance: float = 0.5) -> None:
        from .base import MemoryItem
        self._items[key] = MemoryItem(key=key, content=content, timestamp=time.time(), importance=importance)
        self._access_times[key] = time.time()
        if len(self._items) > self.config.capacity:
            oldest = min(self._access_times, key=self._access_times.get)
            del self._items[oldest]
            del self._access_times[oldest]

    def recall(self, key: str) -> Optional[Any]:
        if key in self._items:
            self._access_times[key] = time.time()
            return self._items[key].content
        return None

    def forget(self, key: str) -> None:
        self._items.pop(key, None)
        self._access_times.pop(key, None)