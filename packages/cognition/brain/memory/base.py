# Copyright (c) Ultrone Contributors. All rights reserved.
"""Base interface for all memory systems."""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger("Ultrone.Brain.Memory.Base")


@dataclass
class MemoryItem:
    """A single item stored in memory."""
    key: str
    content: Any
    timestamp: float = 0.0
    importance: float = 0.5
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class MemoryConfig:
    """Base configuration for memory systems."""
    capacity: int = 10000
    retention_period: float = 3600.0  # seconds


class BaseMemory(ABC):
    """Abstract interface for all memory systems."""

    def __init__(self, config: MemoryConfig):
        self.config = config
        self._items: Dict[str, MemoryItem] = {}

    @abstractmethod
    def store(self, key: str, content: Any, importance: float = 0.5) -> None:
        ...

    @abstractmethod
    def recall(self, key: str) -> Optional[Any]:
        ...

    @abstractmethod
    def forget(self, key: str) -> None:
        ...

    def clear(self) -> None:
        self._items.clear()

    def get_stats(self) -> Dict[str, Any]:
        return {"type": type(self).__name__, "size": len(self._items)}