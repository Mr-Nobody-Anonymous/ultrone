# Copyright (c) Ultrone Contributors. All rights reserved.
"""Multi-sensor fusion for unified contact picture."""

import logging
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import uuid

from ...data.entities import Contact, ThreatLevel, DomainType
from ...data.feeds import SensorFeed, RadarFeed, VisualFeed, SigintFeed, CyberFeed, SonarFeed

logger = logging.getLogger("Ultrone.Brain.Perception.SensorFusion")


@dataclass
class FusedContact:
    """A contact created from fused sensor data."""
    contact_id: str
    domain: DomainType
    position: Tuple[float, float, float]
    velocity: Tuple[float, float, float]
    threat_level: ThreatLevel
    confidence: float  # Combined confidence from all sensors
    source_feeds: List[str]  # Which feeds contributed
    last_update: str
    
    def to_contact(self) -> Contact:
        """Convert to a Contact object."""
        return Contact(
            contact_id=self.contact_id,
            domain=self.domain,
            position=self.position,
            velocity=self.velocity,
            speed=sum(abs(v) for v in self.velocity) / 3,  # Approximate
            heading=0.0,  # Would calculate from velocity
            threat_level=self.threat_level,
            confidence=self.confidence,
        )


class SensorFusion:
    """
    Fuses radar, visual, SIGINT, and cyber feeds into unified contacts.
    
    Implements weighted fusion based on sensor reliability and
    environmental conditions.
    """
    
    # Sensor reliability weights (can be adjusted by environment)
    DEFAULT_WEIGHTS = {
        "radar": 1.0,
        "visual": 0.8,
        "sigint": 0.6,
        "cyber": 0.9,
        "sonar": 0.7,
    }
    
    def __init__(self):
        self.contacts: Dict[str, FusedContact] = {}
        self.sensor_weights = self.DEFAULT_WEIGHTS.copy()
    
    def fuse_feeds(self, feeds: List[SensorFeed], environment_factor: float = 1.0) -> List[FusedContact]:
        """
        Fuse multiple sensor feeds into unified contacts.
        
        Returns list of fused contacts.
        """
        # Apply environment factor to weights
        weights = {k: v * environment_factor for k, v in self.sensor_weights.items()}
        
        # Group feeds by approximate position
        position_groups = self._group_by_position(feeds)
        
        fused_contacts = []
        for group in position_groups:
            fused = self._fuse_group(group, weights)
            if fused:
                self.contacts[fused.contact_id] = fused
                fused_contacts.append(fused)
        
        return fused_contacts
    
    def _group_by_position(self, feeds: List[SensorFeed], tolerance_meters: float = 500) -> List[List[SensorFeed]]:
        """Group feeds that are near each other."""
        groups = []
        used = set()
        
        for feed in feeds:
            if feed in used:
                continue
            
            group = [feed]
            used.add(feed)
            
            for other in feeds:
                if other in used:
                    continue
                
                dx = other.position[0] - feed.position[0]
                dy = other.position[1] - feed.position[1]
                dz = other.position[2] - feed.position[2]
                
                if (dx ** 2 + dy ** 2 + dz ** 2) ** 0.5 < tolerance_meters:
                    group.append(other)
                    used.add(other)
            
            groups.append(group)
        
        return groups
    
    def _fuse_group(self, feeds: List[SensorFeed], weights: Dict[str, float]) -> Optional[FusedContact]:
        """Fuse a group of feeds into a single contact."""
        if not feeds:
            return None
        
        # Weighted average position
        total_weight = 0.0
        x, y, z = 0.0, 0.0, 0.0
        vx, vy, vz = 0.0, 0.0, 0.0
        total_confidence = 0.0
        
        for feed in feeds:
            w = weights.get(feed.sensor_type.value, 0.5)
            x += feed.position[0] * w
            y += feed.position[1] * w
            z += feed.position[2] * w
            vx += feed.metadata.get("velocity_x", 0) * w
            vy += feed.metadata.get("velocity_y", 0) * w
            vz += feed.metadata.get("velocity_z", 0) * w
            total_confidence += feed.confidence * w
            total_weight += w
        
        if total_weight == 0:
            return None
        
        # Determine domain (majority vote weighted)
        domain_counts = {}
        for feed in feeds:
            domain = feed.sensor_type.value
            domain_counts[domain] = domain_counts.get(domain, 0) + 1
        primary_domain = max(domain_counts, key=domain_counts.get)
        
        # Determine threat level
        threat_level = ThreatLevel.MEDIUM  # Default
        for feed in feeds:
            if hasattr(feed, 'threat_classification'):
                threat = feed.threat_classification
                if threat == "imminent":
                    threat_level = ThreatLevel.IMMINENT
                elif threat == "critical":
                    threat_level = ThreatLevel.CRITICAL
        
        return FusedContact(
            contact_id=f"FC-{uuid.uuid4().hex[:8].upper()}",
            domain=DomainType(primary_domain) if primary_domain in [d.value for d in DomainType] else DomainType.GENERAL,
            position=(x/total_weight, y/total_weight, z/total_weight),
            velocity=(vx/total_weight, vy/total_weight, vz/total_weight),
            threat_level=threat_level,
            confidence=min(1.0, total_confidence / total_weight),
            source_feeds=[f.feed_id for f in feeds],
            last_update=feeds[0].detection_time,
        )
    
    def get_contact(self, contact_id: str) -> Optional[FusedContact]:
        """Get a fused contact by ID."""
        return self.contacts.get(contact_id)
    
    def get_all_contacts(self) -> List[FusedContact]:
        """Get all fused contacts."""
        return list(self.contacts.values())
    
    def update_contact(self, contact: FusedContact) -> None:
        """Update an existing contact."""
        if contact.contact_id in self.contacts:
            self.contacts[contact.contact_id] = contact
    
    def remove_contact(self, contact_id: str) -> Optional[FusedContact]:
        """Remove a contact."""
        return self.contacts.pop(contact_id, None)
    
    def get_stats(self) -> dict:
        return {
            "active_contacts": len(self.contacts),
            "sensor_weights": self.sensor_weights.copy(),
        }