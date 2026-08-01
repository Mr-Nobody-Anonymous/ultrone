"""Blackboard-based coordination architecture."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Set

from .base import AIArchitecture, AIArchitectureConfig

logger = logging.getLogger("Ultrone.AIArchitectures.Blackboard")


@dataclass
class BlackboardEntry:
    """An entry on the shared blackboard."""
    key: str
    value: Any
    source: str = ""
    confidence: float = 1.0


class BlackboardSystem(AIArchitecture):
    """Blackboard-based coordination architecture.

    A shared knowledge space where multiple knowledge sources
    (agents/expert systems) can read and write information.
    A scheduler decides which source to activate based on
    the current state of the blackboard.
    """

    def __init__(self, config: Optional[AIArchitectureConfig] = None):
        super().__init__(config or AIArchitectureConfig(name="blackboard"))
        self._blackboard: Dict[str, BlackboardEntry] = {}
        self._knowledge_sources: Dict[str, Callable] = {}
        self._scheduler: Optional[Callable] = None

    def share(self, key: str, value: Any) -> None:
        """Share information on the blackboard (convenience for write)."""
        self.write(key, value, source="share")

    def write(self, key: str, value: Any, source: str = "", confidence: float = 1.0) -> None:
        self._blackboard[key] = BlackboardEntry(key=key, value=value, source=source, confidence=confidence)

    def read(self, key: str) -> Any:
        entry = self._blackboard.get(key)
        return entry.value if entry else None

    def register_source(self, name: str, source_fn: Callable) -> None:
        self._knowledge_sources[name] = source_fn

    def decide(self, state: Dict[str, Any]) -> str:
        # Let the scheduler activate a knowledge source
        if self._scheduler:
            source_name = self._scheduler(self._blackboard, list(self._knowledge_sources.keys()))
            if source_name and source_name in self._knowledge_sources:
                result = self._knowledge_sources[source_name](self._blackboard)
                self._last_action = f"activated_{source_name}"
                return self._last_action
        self._last_action = "idle"
        return "idle"

    def reset(self) -> None:
        self._blackboard.clear()
