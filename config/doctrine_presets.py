# Copyright (c) Ultrone Contributors. All rights reserved.
"""Military doctrine presets for tactical behavior configuration."""

from dataclasses import dataclass
from enum import Enum
from typing import Dict, Any


class DoctrineType(Enum):
    """Doctrine types defining tactical behavior patterns."""
    AGGRESSIVE = "aggressive"
    DEFENSIVE = "defensive"
    BALANCED = "balanced"
    ASYMMETRIC = "asymmetric"


@dataclass
class DoctrinePreset:
    """Configuration of tactical doctrine parameters."""
    name: str
    doctrine_type: DoctrineType
    description: str
    
    # Core behavior weights (0.0-1.0)
    aggression: float      # Willingness to engage first
    risk_tolerance: float  # Willingness to accept losses
    initiative: float      # Proactive vs reactive
    conservation: float    # Resource preservation priority
    
    # Sensor thresholds
    detection_sensitivity: float  # How easily threats are detected
    confirmation_threshold: float # Confidence needed to classify target
    
    # Engagement rules
    engage_on_sight: bool    # Engage without positive ID
    prefer_standoff: bool    # Prefer long-range over close combat
    
    # Evolution parameters
    innovation_rate: float    # Willingness to try new tactics
    
    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "doctrine_type": self.doctrine_type.value,
            "description": self.description,
            "aggression": self.aggression,
            "risk_tolerance": self.risk_tolerance,
            "initiative": self.initiative,
            "conservation": self.conservation,
            "detection_sensitivity": self.detection_sensitivity,
            "confirmation_threshold": self.confirmation_threshold,
            "engage_on_sight": self.engage_on_sight,
            "prefer_standoff": self.prefer_standoff,
            "innovation_rate": self.innovation_rate,
        }


# Predefined doctrine presets
DOCTRINE_PRESETS: Dict[DoctrineType, DoctrinePreset] = {
    DoctrineType.AGGRESSIVE: DoctrinePreset(
        name="AirLand Battle Doctrine",
        doctrine_type=DoctrineType.AGGRESSIVE,
        description="Proactive attack with overwhelming force",
        aggression=0.9,
        risk_tolerance=0.8,
        initiative=0.9,
        conservation=0.4,
        detection_sensitivity=0.85,
        confirmation_threshold=0.6,
        engage_on_sight=True,
        prefer_standoff=False,
        innovation_rate=0.3,
    ),
    DoctrineType.DEFENSIVE: DoctrinePreset(
        name="Attritional Defense",
        doctrine_type=DoctrineType.DEFENSIVE,
        description="Defend in depth, minimize losses",
        aggression=0.3,
        risk_tolerance=0.2,
        initiative=0.4,
        conservation=0.9,
        detection_sensitivity=0.7,
        confirmation_threshold=0.9,
        engage_on_sight=False,
        prefer_standoff=True,
        innovation_rate=0.15,
    ),
    DoctrineType.BALANCED: DoctrinePreset(
        name="Combined Arms Maneuver",
        doctrine_type=DoctrineType.BALANCED,
        description="Flexible response across all domains",
        aggression=0.6,
        risk_tolerance=0.5,
        initiative=0.6,
        conservation=0.6,
        detection_sensitivity=0.8,
        confirmation_threshold=0.75,
        engage_on_sight=False,
        prefer_standoff=True,
        innovation_rate=0.25,
    ),
    DoctrineType.ASYMMETRIC: DoctrinePreset(
        name="Network-Centric Guerrilla",
        doctrine_type=DoctrineType.ASYMMETRIC,
        description="Decentralized operations, exploit vulnerabilities",
        aggression=0.7,
        risk_tolerance=0.6,
        initiative=0.95,
        conservation=0.8,
        detection_sensitivity=0.9,
        confirmation_threshold=0.5,
        engage_on_sight=True,
        prefer_standoff=True,
        innovation_rate=0.6,
    ),
}


def get_doctrine_preset(doctrine_type: DoctrineType) -> DoctrinePreset:
    """Get a doctrine preset by type."""
    return DOCTRINE_PRESETS.get(doctrine_type)


def get_all_doctrines() -> Dict[DoctrineType, DoctrinePreset]:
    """Get all available doctrine presets."""
    return DOCTRINE_PRESETS.copy()