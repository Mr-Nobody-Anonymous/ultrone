# Copyright (c) Ultrone Contributors. All rights reserved.
"""Visualization utilities for situational awareness.

Provides:

* world state rendering to dict/JSON
* entity state serialization
* scene graph serialization
* semantic map serialization
* text-based situational summary
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from .types import (
    Relationship,
    TrackedEntity,
    WorldSnapshot,
)

__all__ = [
    "VisualizationEngine",
    "VisualizationConfig",
]


class VisualizationConfig:
    """Configuration for the visualization engine."""

    def __init__(
        self,
        *,
        include_history: bool = False,
        include_relationships: bool = True,
        max_entities: int = 1000,
    ) -> None:
        self.include_history = include_history
        self.include_relationships = include_relationships
        self.max_entities = max_entities


class VisualizationEngine:
    """Serializes world state for visualization and analysis."""

    def __init__(self, *, config: Optional[VisualizationConfig] = None) -> None:
        self._config = config or VisualizationConfig()

    def entity_to_dict(self, entity: TrackedEntity) -> Dict[str, Any]:
        """Serialize a tracked entity to a dictionary."""
        data: Dict[str, Any] = {
            "entity_id": str(entity.entity_id),
            "entity_type": entity.entity_type.value,
            "category": entity.category.value,
            "disposition": entity.disposition.value,
            "position": entity.state.position.as_array().tolist(),
            "velocity": entity.state.velocity.as_array().tolist(),
            "confidence": entity.confidence,
            "uncertainty": entity.uncertainty,
            "observation_count": entity.observation_count,
            "created_at": entity.created_at.isoformat(),
            "updated_at": entity.updated_at.isoformat(),
            "inferred_properties": dict(entity.inferred_properties),
            "labels": dict(entity.labels),
        }
        if self._config.include_history:
            data["history"] = [
                s.position.as_array().tolist() for s in entity.history
            ]
        return data

    def relationship_to_dict(self, relationship: Relationship) -> Dict[str, Any]:
        """Serialize a relationship to a dictionary."""
        return {
            "relationship_id": relationship.relationship_id,
            "source_id": str(relationship.source_id),
            "target_id": str(relationship.target_id),
            "relationship_type": relationship.relationship_type.value,
            "confidence": relationship.confidence,
        }

    def snapshot_to_dict(self, snapshot: WorldSnapshot) -> Dict[str, Any]:
        """Serialize a world snapshot to a dictionary."""
        entities = snapshot.entities[: self._config.max_entities]
        data: Dict[str, Any] = {
            "captured_at": snapshot.captured_at.isoformat(),
            "sequence": snapshot.sequence,
            "entity_count": len(snapshot.entities),
            "relationship_count": len(snapshot.relationships),
            "observation_count": len(snapshot.observations),
            "entities": [self.entity_to_dict(e) for e in entities],
        }
        if self._config.include_relationships:
            data["relationships"] = [
                self.relationship_to_dict(r) for r in snapshot.relationships
            ]
        return data

    def situational_summary(
        self, snapshot: WorldSnapshot
    ) -> str:
        """Generate a human-readable situational summary."""
        lines = [
            "=" * 50,
            "SITUATIONAL AWARENESS SUMMARY",
            "=" * 50,
            f"Sequence: {snapshot.sequence}",
            f"Entities: {len(snapshot.entities)}",
            f"Relationships: {len(snapshot.relationships)}",
            f"Observations: {len(snapshot.observations)}",
            "",
            "ENTITIES:",
        ]

        for entity in snapshot.entities[:20]:
            lines.append(
                f"  - {entity.entity_type.value} [{entity.category.value}] "
                f"conf={entity.confidence:.2f} unc={entity.uncertainty:.2f} "
                f"pos=({entity.state.position.x:.1f}, {entity.state.position.y:.1f})"
            )

        if len(snapshot.entities) > 20:
            lines.append(f"  ... and {len(snapshot.entities) - 20} more")

        lines.append("=" * 50)
        return "\n".join(lines)

    def to_json(self, snapshot: WorldSnapshot) -> str:
        """Serialize a world snapshot to JSON."""
        import json

        return json.dumps(self.snapshot_to_dict(snapshot), indent=2)