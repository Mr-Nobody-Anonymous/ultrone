# Copyright (c) Ultrone Contributors. All rights reserved.
"""Associative memory for pattern-based recall."""

from __future__ import annotations

import logging
import numpy as np
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from .base import BaseMemory, MemoryConfig

logger = logging.getLogger("Ultrone.Brain.Memory.Associative")


@dataclass
class AssociativeConfig(MemoryConfig):
    """Configuration for associative memory."""
    similarity_threshold: float = 0.7


class AssociativeMemory(BaseMemory):
    """Associative memory for pattern-based recall using similarity."""

    def __init__(self, config: Optional[AssociativeConfig] = None):
        super().__init__(config or AssociativeConfig())

    def store(self, key: str, content: Any, importance: float = 0.5) -> None:
        from .base import MemoryItem
        import time
        self._items[key] = MemoryItem(key=key, content=content, timestamp=time.time(), importance=importance)

    def recall(self, key: str) -> Optional[Any]:
        item = self._items.get(key)
        return item.content if item else None

    def recall_by_pattern(self, pattern: str) -> List[Any]:
        return [item.content for item in self._items.values() if pattern.lower() in str(item.content).lower()]

    def associate(self, trigger: str, response: Any) -> None:
        """Associate a trigger pattern with a response.

        Args:
            trigger: The key/pattern that triggers recall.
            response: The response content to recall.
        """
        self.store(trigger, response)

    def forget(self, key: str) -> None:
        self._items.pop(key, None)
