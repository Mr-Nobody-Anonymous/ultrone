# Copyright (c) Ultrone Contributors. All rights reserved.
"""Memory consolidation for transferring between memory tiers."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from .base import BaseMemory, MemoryConfig, MemoryItem

logger = logging.getLogger("Ultrone.Brain.Memory.Consolidation")


@dataclass
class ConsolidationConfig(MemoryConfig):
    """Configuration for memory consolidation."""
    consolidation_interval: float = 300.0
    importance_threshold: float = 0.7


class MemoryConsolidation:
    """Memory consolidation process that transfers important episodic
    memories to semantic memory for long-term retention."""

    def __init__(self, config: Optional[ConsolidationConfig] = None):
        self.config = config or ConsolidationConfig()
        self._episodic: Optional[BaseMemory] = None
        self._semantic: Optional[BaseMemory] = None

    def set_memories(self, episodic: BaseMemory, semantic: BaseMemory) -> None:
        self._episodic = episodic
        self._semantic = semantic

    def consolidate(self) -> int:
        """Transfer important episodic memories to semantic memory."""
        if not self._episodic or not self._semantic:
            return 0
        transferred = 0
        for key, item in list(self._episodic._items.items()):
            if item.importance >= self.config.importance_threshold:
                self._semantic.store(f"consolidated_{key}", item.content, item.importance)
                transferred += 1
        return transferred

    def get_stats(self) -> Dict[str, Any]:
        return {"type": "MemoryConsolidation"}