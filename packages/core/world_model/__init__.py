# Copyright (c) Ultrone Contributors. All rights reserved.
"""ULTRONE world model — one canonical state layer for the whole platform.

Every subsystem (perception, simulation, agents, external data) publishes
*entities* with stable identifiers, composable state, confidence and
provenance. Everything else (reasoning, planning, UI) reads from here.

This module is the seed of that single world model. It composes the layers
that already exist instead of replacing them:

    brain/perception/situational_awareness/world_model.py   (SA layer)
    cognitive/world_model_layer.py                          (cognitive layer)
    simulation/sim/world_state.py + simulation/sim/world_modeling/  (sim layer)

Design (entity-as-components, Lattice-style):
    - ``Entity`` is composed of state components, not a rigid class hierarchy
    - every entity has a stable ``entity_id`` and ``type``
    - every component value carries ``confidence`` and ``provenance``
    - updates arrive as ``EntityUpdated`` events, never via direct mutation
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class Provenance:
    """Where a piece of state came from (observation -> source -> model)."""

    source: str                      # e.g. "sensor:radar-3", "agent:recon-1"
    transformation: str = ""         # e.g. "sensor_fusion", "trajectory_predictor"
    model: str = ""                  # e.g. "gru-trajectory-v2"
    observed_at: float = field(default_factory=time.time)
    note: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "source": self.source,
            "transformation": self.transformation,
            "model": self.model,
            "observed_at": self.observed_at,
            "note": self.note,
        }


@dataclass
class Component:
    """One composable state component (position, velocity, sensors, ...)."""

    value: Any
    confidence: float = 1.0
    provenance: List[Provenance] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "value": self.value,
            "confidence": self.confidence,
            "provenance": [p.to_dict() for p in self.provenance],
        }


@dataclass
class Entity:
    """Canonical world-model entity: id + type + composable components."""

    entity_id: str = field(default_factory=lambda: f"entity_{uuid.uuid4().hex[:8]}")
    type: str = "unknown"
    status: str = "active"
    components: Dict[str, Component] = field(default_factory=dict)
    updated_at: float = field(default_factory=time.time)

    def set(self, name: str, value: Any, confidence: float = 1.0,
            provenance: Optional[List[Provenance]] = None) -> None:
        """Set one component with confidence + provenance."""
        self.components[name] = Component(
            value=value,
            confidence=confidence,
            provenance=provenance or [],
        )
        self.updated_at = time.time()

    def get(self, name: str, default: Any = None) -> Any:
        comp = self.components.get(name)
        return comp.value if comp is not None else default

    def to_dict(self) -> Dict[str, Any]:
        return {
            "entity_id": self.entity_id,
            "type": self.type,
            "status": self.status,
            "components": {k: c.to_dict() for k, c in self.components.items()},
            "updated_at": self.updated_at,
        }


@dataclass
class EntityUpdated:
    """World-model event stream payload (drives UI + cognition)."""

    entity_id: str
    changes: Dict[str, Any]
    confidence: float = 1.0
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "ENTITY_UPDATED",
            "entity_id": self.entity_id,
            "changes": self.changes,
            "confidence": self.confidence,
            "timestamp": self.timestamp,
        }


class WorldModel:
    """In-memory canonical state store (Postgres/Redis-backed later)."""

    def __init__(self) -> None:
        self._entities: Dict[str, Entity] = {}

    def upsert(self, entity: Entity) -> Entity:
        self._entities[entity.entity_id] = entity
        return entity

    def get(self, entity_id: str) -> Optional[Entity]:
        return self._entities.get(entity_id)

    def find(self, entity_type: Optional[str] = None,
             status: Optional[str] = None) -> List[Entity]:
        out = list(self._entities.values())
        if entity_type is not None:
            out = [e for e in out if e.type == entity_type]
        if status is not None:
            out = [e for e in out if e.status == status]
        return out

    def apply(self, event: EntityUpdated) -> Optional[Entity]:
        """Apply an ``ENTITY_UPDATED`` event to the canonical state."""
        entity = self._entities.get(event.entity_id)
        if entity is None:
            return None
        for name, value in event.changes.items():
            if name == "status":
                entity.status = str(value)
            entity.set(name, value, confidence=event.confidence,
                       provenance=[Provenance(source="event", note="ENTITY_UPDATED")])
        return entity

    def snapshot(self) -> List[Dict[str, Any]]:
        return [e.to_dict() for e in self._entities.values()]


#: Shared singleton for processes that want one store without DI plumbing.
default_world_model = WorldModel()

__all__ = [
    "Provenance", "Component", "Entity", "EntityUpdated", "WorldModel",
    "default_world_model",
]
