# Copyright (c) Ultrone Contributors. All rights reserved.
"""Military entity and contact data models for battlefield simulation."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Tuple


class DomainType(Enum):
    """Operational domain types."""
    AIR = "air"
    LAND = "land"
    SEA = "sea"
    CYBER = "cyber"
    SPACE = "space"
    GENERAL = "general"


class ThreatLevel(Enum):
    """Threat classification levels per doctrinal standards."""
    UNKNOWN = 0
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4
    IMMINENT = 5


class AgentState(Enum):
    """Generic agent state machine states."""
    STANDBY = "standby"
    ACTIVE = "active"
    ENGAGED = "engaged"
    RETURNING = "returning"
    OFFLINE = "offline"
    ERROR = "error"


@dataclass
class Contact:
    """A detected entity in the battlespace (friend or foe)."""
    contact_id: str
    domain: DomainType
    position: Tuple[float, float, float]  # x, y, z in meters
    velocity: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    altitude: float = 0.0
    speed: float = 0.0
    heading: float = 0.0
    threat_level: ThreatLevel = ThreatLevel.UNKNOWN
    confidence: float = 1.0  # Classification confidence 0.0-1.0
    detected_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    last_update: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    team: Optional[str] = None  # "blue", "red", "neutral", or None for unknown
    capabilities: List[str] = field(default_factory=list)
    emissions: Dict[str, float] = field(default_factory=dict)  # SIGINT signature data
    
    def update_position(self, new_pos: Tuple[float, float, float], velocity: Tuple[float, float, float] = None) -> None:
        """Update contact position and velocity."""
        self.position = new_pos
        if velocity:
            self.velocity = velocity
        self.last_update = datetime.utcnow().isoformat()
    
    def get_distance_to(self, other: 'Contact') -> float:
        """Calculate 3D distance to another contact."""
        return ((self.position[0] - other.position[0]) ** 2 + 
                (self.position[1] - other.position[1]) ** 2 + 
                (self.position[2] - other.position[2]) ** 2) ** 0.5
    
    def to_dict(self) -> dict:
        return {
            "contact_id": self.contact_id,
            "domain": self.domain.value,
            "position": {"x": self.position[0], "y": self.position[1], "z": self.position[2]},
            "altitude": self.altitude,
            "speed": self.speed,
            "heading": self.heading,
            "threat_level": self.threat_level.name,
            "confidence": self.confidence,
            "team": self.team,
            "detected_at": self.detected_at,
            "capabilities": self.capabilities,
        }


@dataclass
class Unit:
    """A controllable military asset in the simulation."""
    unit_id: str
    domain: DomainType
    unit_type: str
    position: Tuple[float, float, float]
    state: AgentState = AgentState.STANDBY
    team: str = "blue"
    health: float = 1.0  # 0.0 destroyed, 1.0 full health
    fuel: float = 1.0
    ammunition: int = 100
    sensor_range: float = 50000.0  # meters
    weapons: List[str] = field(default_factory=list)
    max_speed: float = 100.0  # domain-specific max speed
    max_altitude: float = 10000.0  # for air assets
    role: str = "general"
    parent_unit: Optional[str] = None  # Formation hierarchy
    
    def take_damage(self, damage: float) -> bool:
        """Apply damage. Returns True if destroyed."""
        self.health = max(0.0, self.health - damage)
        if self.health <= 0.0:
            self.state = AgentState.OFFLINE
            return True
        return False
    
    def consume_ammunition(self, amount: int = 1) -> bool:
        """Consume ammunition. Returns True if available."""
        if self.ammunition >= amount:
            self.ammunition -= amount
            return True
        return False
    
    def is_operational(self) -> bool:
        """Check if unit can perform missions."""
        return self.state not in (AgentState.OFFLINE, AgentState.ERROR) and self.health > 0.1
    
    def to_dict(self) -> dict:
        return {
            "unit_id": self.unit_id,
            "domain": self.domain.value,
            "unit_type": self.unit_type,
            "position": {"x": self.position[0], "y": self.position[1], "z": self.position[2]},
            "state": self.state.value,
            "team": self.team,
            "health": self.health,
            "fuel": self.fuel,
            "ammunition": self.ammunition,
            "sensor_range": self.sensor_range,
            "role": self.role,
        }


@dataclass
class Formation:
    """A group of units operating together."""
    formation_id: str
    name: str
    units: List[str]  # unit_ids
    formation_type: str  # "wedge", "line", "column", "box", "dispersed"
    leader_unit: Optional[str] = None
    role: str = "general"
    cohesion: float = 1.0  # 0.0 scattered, 1.0 tight formation
    
    def add_unit(self, unit_id: str) -> None:
        if unit_id not in self.units:
            self.units.append(unit_id)
    
    def remove_unit(self, unit_id: str) -> None:
        if unit_id in self.units:
            self.units.remove(unit_id)
    
    def get_size(self) -> int:
        return len(self.units)


@dataclass
class EngagementRecord:
    """Record of an engagement between units."""
    engagement_id: str
    attacker_id: str
    target_id: str
    domain: DomainType
    weapon_type: str
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    impact_position: Optional[Tuple[float, float, float]] = None
    hit: bool = False
    damage: float = 0.0
    duration_ms: float = 0.0
    kill_chain_phase: str = "engage"
    collateral: List[str] = field(default_factory=list)  # Other units affected
    
    def to_dict(self) -> dict:
        return {
            "engagement_id": self.engagement_id,
            "attacker_id": self.attacker_id,
            "target_id": self.target_id,
            "domain": self.domain.value,
            "weapon_type": self.weapon_type,
            "timestamp": self.timestamp,
            "hit": self.hit,
            "damage": self.damage,
            "duration_ms": self.duration_ms,
            "collateral": self.collateral,
        }