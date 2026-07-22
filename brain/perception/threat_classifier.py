# Copyright (c) Ultrone Contributors. All rights reserved.
"""Threat classification using weighted matrix scoring."""

import logging
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import random

from ...data.entities import Contact, ThreatLevel, DomainType

logger = logging.getLogger("Ultrone.Brain.Perception.ThreatClassifier")


@dataclass
class ThreatScore:
    """Threat assessment result."""
    contact_id: str
    threat_level: ThreatLevel
    score: float  # 0.0-100.0 composite score
    components: Dict[str, float]  # Individual factor scores
    confidence: float
    
    def to_dict(self) -> dict:
        return {
            "contact_id": self.contact_id,
            "threat_level": self.threat_level.name,
            "score": self.score,
            "confidence": self.confidence,
            "components": self.components,
        }


class ThreatClassifier:
    """
    Weighted matrix threat scoring system.
    
    Evaluates contacts based on multiple factors:
    - Asset type and capabilities
    - Distance and trajectory
    - Speed and heading
    - Classification confidence
    - Historical patterns
    """
    
    # Weapon effectiveness matrix against target types
    WEAPON_MATRIX = {
        DomainType.AIR: {
            "fighter": 0.9, "drone": 0.7, "missile": 1.0,
            "sam": 0.8, "bomber": 0.95,
        },
        DomainType.LAND: {
            "tank": 0.9, "infantry": 0.4, "artillery": 0.85,
            "sam": 0.7, "mobile_missile": 0.9,
        },
        DomainType.SEA: {
            "vessel": 0.8, "submarine": 0.95, "carrier": 1.0,
        },
        DomainType.CYBER: {
            "recon": 0.6, "exploit": 1.0, "malware": 0.85,
        },
        DomainType.SPACE: {
            "satellite": 0.7, "weapon": 0.9,
        },
    }
    
    # Threat factor weights
    FACTOR_WEIGHTS = {
        "capability": 0.30,      # Weapons/capabilities
        "proximity": 0.25,     # Distance (closer = more threatening)
        "velocity": 0.20,      # Speed toward us
        "trajectory": 0.15,    # Heading toward our forces
        "confidence": 0.10,    # Our confidence in classification
    }
    
    def __init__(self, threat_thresholds: Dict[str, float] = None):
        self.thresholds = threat_thresholds or {
            "critical": 80.0,
            "high": 60.0,
            "medium": 40.0,
            "low": 20.0,
        }
    
    def classify(self, contact: Contact, blue_positions: List[Tuple[float, float, float]] = None) -> ThreatScore:
        """
        Classify a contact's threat level using weighted scoring.
        
        Returns threat score with confidence.
        """
        components = {}
        
        # Capability score based on contact type
        capability_score = self._score_capability(contact)
        components["capability"] = capability_score
        
        # Proximity score (closer = higher threat)
        proximity_score = self._score_proximity(contact, blue_positions)
        components["proximity"] = proximity_score
        
        # Velocity score (faster = more threatening)
        velocity_score = self._score_velocity(contact)
        components["velocity"] = velocity_score
        
        # Trajectory score
        trajectory_score = self._score_trajectory(contact, blue_positions)
        components["trajectory"] = trajectory_score
        
        # Confidence score
        confidence_score = contact.confidence
        components["confidence"] = confidence_score
        
        # Weighted composite
        composite = sum(
            components.get(k, 0) * v
            for k, v in self.FACTOR_WEIGHTS.items()
        )
        
        # Determine threat level
        if composite >= self.thresholds["critical"]:
            threat_level = ThreatLevel.CRITICAL
        elif composite >= self.thresholds["high"]:
            threat_level = ThreatLevel.HIGH
        elif composite >= self.thresholds["medium"]:
            threat_level = ThreatLevel.MEDIUM
        elif composite >= self.thresholds["low"]:
            threat_level = ThreatLevel.LOW
        else:
            threat_level = ThreatLevel.UNKNOWN
        
        # Overall confidence
        overall_confidence = min(1.0, contact.confidence + (composite / 100.0 * 0.3))
        
        return ThreatScore(
            contact_id=contact.contact_id,
            threat_level=threat_level,
            score=composite,
            components=components,
            confidence=overall_confidence,
        )
    
    def _score_capability(self, contact: Contact) -> float:
        """Score based on contact's capabilities."""
        # Would check contact capabilities list
        capability_levels = {
            "missile": 1.0, "fighter": 0.9, "bomber": 0.95,
            "tank": 0.8, "artillery": 0.75, "sam": 0.85,
            "submarine": 0.9, "carrier": 0.95,
            "satellite": 0.7, "cyber": 0.8,
        }
        
        # Estimate based on domain
        if contact.domain == DomainType.AIR:
            return random.uniform(0.7, 1.0)
        elif contact.domain == DomainType.LAND:
            return random.uniform(0.6, 0.9)
        elif contact.domain == DomainType.SEA:
            return random.uniform(0.7, 0.95)
        elif contact.domain == DomainType.CYBER:
            return random.uniform(0.5, 0.85)
        elif contact.domain == DomainType.SPACE:
            return random.uniform(0.6, 0.8)
        return 0.5
    
    def _score_proximity(self, contact: Contact, positions: List[Tuple[float, float, float]] = None) -> float:
        """Score based on distance to friendly forces."""
        # Mock distance-based scoring
        # In reality, would calculate distance to nearest friendly position
        return random.uniform(0.3, 1.0)  # Placeholder
    
    def _score_velocity(self, contact: Contact) -> float:
        """Score based on speed."""
        # Higher speed = more threatening (normalized to 0-100)
        max_speed = 1000.0  # m/s
        normalized = min(1.0, contact.speed / max_speed)
        return normalized * 100.0
    
    def _score_trajectory(self, contact: Contact, positions: List[Tuple[float, float, float]] = None) -> float:
        """Score based on heading toward friendly forces."""
        return random.uniform(0.4, 1.0)  # Placeholder
    
    def get_stats(self) -> dict:
        return {
            "thresholds": self.thresholds.copy(),
            "factor_weights": self.FACTOR_WEIGHTS.copy(),
        }