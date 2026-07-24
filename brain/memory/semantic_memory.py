# Copyright (c) Ultrone Contributors. All rights reserved.
"""Semantic memory for storing general knowledge and concepts."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from .base import BaseMemory, MemoryConfig

logger = logging.getLogger("Ultrone.Brain.Memory.Semantic")


@dataclass
class SemanticConfig(MemoryConfig):
    """Configuration for semantic memory."""
    abstraction_level: float = 0.5


class SemanticMemory(BaseMemory):
    """Semantic memory stores general knowledge, concepts, and abstractions."""

    def __init__(self, config: Optional[SemanticConfig] = None):
        super().__init__(config or SemanticConfig())

    def store(self, key: str, content: Any, importance: float = 0.5) -> None:
        from .base import MemoryItem
        import time
        self._items[key] = MemoryItem(key=key, content=content, timestamp=time.time(), importance=importance)

    def recall(self, key: str) -> Optional[Any]:
        item = self._items.get(key)
        return item.content if item else None

    def query(self, concept: str) -> List[Any]:
        return [item.content for item in self._items.values() if concept.lower() in item.key.lower()]

    def forget(self, key: str) -> None:
        self._items.pop(key, None)