# Copyright (c) Ultrone Contributors. All rights reserved.
"""Context engine for situational awareness.

Assembles contextual information about the environment, entities, and
situations. Provides:

* context snapshots for entities
* environmental context (terrain, weather, infrastructure)
* situational context (threats, anomalies, predictions)
* context-based reasoning support
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

from .types import (
    TrackedEntity,
    utc_now,
)

__all__ = [
    "ContextSnapshot",
    "ContextEngine",
    "ContextEngineConfig",
]


@dataclass
class ContextSnapshot:
    """A snapshot of contextual information for an entity or situation."""

    target_id: str
    captured_at: datetime = field(default_factory=utc_now)
    environmental: Dict[str, Any] = field(default_factory=dict)
    situational: Dict[str, Any] = field(default_factory=dict)
    entity_context: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


class ContextEngineConfig:
    """Configuration for the context engine."""

    def __init__(
        self,
        *,
        max_context_history: int = 1000,
        include_environment: bool = True,
        include_situational: bool = True,
    ) -> None:
        self.max_context_history = max_context_history
        self.include_environment = include_environment
        self.include_situational = include_situational


class ContextEngine:
    """Assembles and maintains contextual information."""

    def __init__(self, *, config: Optional[ContextEngineConfig] = None) -> None:
        self._config = config or ContextEngineConfig()
        self._snapshots: List[ContextSnapshot] = []
        self._environmental: Dict[str, Any] = {}
        self._situational: Dict[str, Any] = {}

    def set_environmental(self, key: str, value: Any) -> None:
        """Set an environmental context value (terrain, weather, etc.)."""
        self._environmental[key] = value

    def set_situational(self, key: str, value: Any) -> None:
        """Set a situational context value (threats, anomalies, etc.)."""
        self._situational[key] = value

    def update_environmental(self, values: Dict[str, Any]) -> None:
        self._environmental.update(values)

    def update_situational(self, values: Dict[str, Any]) -> None:
        self._situational.update(values)

    def snapshot_for(
        self,
        entity: Optional[TrackedEntity] = None,
        *,
        target_id: Optional[str] = None,
    ) -> ContextSnapshot:
        """Build a context snapshot for an entity or situation."""
        target = target_id or (str(entity.entity_id) if entity else "global")

        entity_context: Dict[str, Any] = {}
        if entity is not None:
            entity_context = {
                "entity_type": entity.entity_type.value,
                "category": entity.category.value,
                "disposition": entity.disposition.value,
                "position": entity.state.position.as_array().tolist(),
                "velocity": entity.state.velocity.as_array().tolist(),
                "confidence": entity.confidence,
                "uncertainty": entity.uncertainty,
                "observation_count": entity.observation_count,
                "inferred_properties": dict(entity.inferred_properties),
            }

        snapshot = ContextSnapshot(
            target_id=target,
            environmental=dict(self._environmental) if self._config.include_environment else {},
            situational=dict(self._situational) if self._config.include_situational else {},
            entity_context=entity_context,
        )
        self._snapshots.append(snapshot)
        if len(self._snapshots) > self._config.max_context_history:
            self._snapshots = self._snapshots[-self._config.max_context_history :]
        return snapshot

    def get_environmental(self, key: str) -> Optional[Any]:
        return self._environmental.get(key)

    def get_situational(self, key: str) -> Optional[Any]:
        return self._situational.get(key)

    def snapshots(self, limit: Optional[int] = None) -> List[ContextSnapshot]:
        snapshots = self._snapshots
        if limit is not None:
            snapshots = snapshots[-limit:]
        return list(snapshots)

    def clear(self) -> None:
        self._snapshots.clear()
        self._environmental.clear()
        self._situational.clear()