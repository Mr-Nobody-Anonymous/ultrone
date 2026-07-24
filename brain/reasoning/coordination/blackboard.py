# Copyright (c) Ultrone Contributors. All rights reserved.
"""Blackboard architecture for shared knowledge access."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .base import BaseCoordinator, CoordinationConfig

logger = logging.getLogger("Ultrone.Brain.Reasoning.Coordination.Blackboard")


@dataclass
class BlackboardConfig(CoordinationConfig):
    """Configuration for blackboard system."""
    max_entries: int = 1000
    entry_ttl: int = 100  # ticks before auto-cleanup


class BlackboardSystem(BaseCoordinator):
    """Shared blackboard architecture for multi-agent coordination.

    Agents post and read information from a shared space, enabling
    indirect coordination through shared knowledge.
    """

    def __init__(self, config: Optional[BlackboardConfig] = None):
        super().__init__(config or BlackboardConfig())
        self._entries: Dict[str, Any] = {}
        self._entry_ttl: Dict[str, int] = {}

    def post(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Post information to the blackboard."""
        self._entries[key] = value
        self._entry_ttl[key] = ttl or self._config.entry_ttl
        if len(self._entries) > self._config.max_entries:
            oldest = min(self._entry_ttl, key=self._entry_ttl.get)
            del self._entries[oldest]
            del self._entry_ttl[oldest]

    def read(self, key: str) -> Optional[Any]:
        """Read information from the blackboard."""
        return self._entries.get(key)

    def query(self, pattern: str) -> Dict[str, Any]:
        """Query entries matching a pattern."""
        return {k: v for k, v in self._entries.items() if pattern in k}

    def coordinate(self, context: Dict[str, Any]) -> Dict[str, Any]:
        postings = context.get("postings", {})
        for k, v in postings.items():
            self.post(k, v)
        reads = context.get("reads", [])
        results = {k: self.read(k) for k in reads}
        # Decay TTLs
        for k in list(self._entry_ttl.keys()):
            self._entry_ttl[k] -= 1
            if self._entry_ttl[k] <= 0:
                del self._entries[k]
                del self._entry_ttl[k]
        return {"results": results, "entries_count": len(self._entries)}

    def get_stats(self) -> Dict[str, Any]:
        return {"type": "BlackboardSystem", "entries": len(self._entries)}