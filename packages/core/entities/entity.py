# Copyright (c) Ultrone Contributors. All rights reserved.
"""Canonical Entity definition."""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


class EntityStatus(str, Enum):
    """Lifecycle status of an entity."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    UNKNOWN = "unknown"
    DESTROYED = "destroyed"
    PENDING = "pending"
    DEGRADED = "degraded"
    ENGAGED = "engaged"


@dataclass
class Position:
    """Geographic or simulation-space position."""
    lat: float = 0.0
    lng: float = 0.0
    alt: float = 0.0


@dataclass
class Velocity:
    """3D velocity vector."""
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0


@dataclass
class Observation:
    """A single observation of an entity."""
    timestamp: str = ""
    source: str = ""
    description: str = ""
    confidence: float = 1.0
    raw_data: Optional[Dict[str, Any]] = None


@dataclass
class Relationship:
    """A relationship between two entities."""
    target_id: str = ""
    relation: str = ""
    confidence: float = 1.0
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class Entity:
    """
    Canonical ULTRONE Entity.

    The fundamental unit of the ULTRONE world model. Every tracked
    object, agent, sensor, region, or concept is represented as an Entity.
    """
    entity_id: str = field(default_factory=lambda: f"entity_{uuid.uuid4().hex[:8]}")
    type: str = "unknown"
    status: EntityStatus = EntityStatus.UNKNOWN
    position: Optional[Position] = None
    velocity: Optional[Velocity] = None
    sensors: List[str] = field(default_factory=list)
    observations: List[Observation] = field(default_factory=list)
    relationships: List[Relationship] = field(default_factory=list)
    confidence: float = 0.0
    provenance: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    def add_observation(self, obs: Observation) -> None:
        """Add an observation and update timestamp."""
        self.observations.append(obs)
        self.updated_at = datetime.utcnow().isoformat()

    def add_relationship(self, rel: Relationship) -> None:
        """Add a relationship to another entity."""
        self.relationships.append(rel)
        self.updated_at = datetime.utcnow().isoformat()

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        from dataclasses import asdict
        return asdict(self)
