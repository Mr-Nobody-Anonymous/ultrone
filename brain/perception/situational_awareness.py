# Copyright (c) Ultrone Contributors. All rights reserved.
"""Common Operating Picture with confidence levels."""

from __future__ import annotations

import logging
from typing import Dict, List, Optional, Tuple, TYPE_CHECKING
from dataclasses import dataclass, field
import random

logger = logging.getLogger("Ultrone.Brain.Perception.SituationalAwareness")

if TYPE_CHECKING:
    from ...data.entities import Contact, ThreatLevel, DomainType, Unit
    from .sensor_fusion import SensorFusion, FusedContact
    from .threat_classifier import ThreatClassifier, ThreatScore


@dataclass
class COPContact:
    """Contact in the Common Operating Picture."""
    contact: Any  # Contact
    threat_score: Optional[Any] = None  # ThreatScore
    last_seen: str = ""
    track_quality: float = 1.0  # 0.0-1.0 quality of track
    fusion_sources: int = 1

    def to_dict(self) -> dict:
        return {
            "contact_id": self.contact.contact_id,
            "domain": self.contact.domain.value,
            "position": {"x": self.contact.position[0], "y": self.contact.position[1], "z": self.contact.position[2]},
            "threat_level": self.contact.threat_level.name,
            "confidence": self.contact.confidence,
            "threat_score": self.threat_score.score if self.threat_score else 0,
            "track_quality": self.track_quality,
        }


class SituationalAwareness:
    """
    Builds and maintains the Common Operating Picture (COP).

    Integrates fused contacts with threat assessments and
    confidence levels to provide complete battlefield visualization.
    """

    def __init__(self):
        # Late imports to avoid circular dependencies
        from ...data.entities import Contact, ThreatLevel, DomainType, Unit
        from .sensor_fusion import SensorFusion
        from .threat_classifier import ThreatClassifier
        
        self.contacts: Dict[str, COPContact] = {}
        self.units: Dict[str, Unit] = {}
        self._sensor_fusion: SensorFusion = SensorFusion()
        self._threat_classifier: ThreatClassifier = ThreatClassifier()

    def update(self, feeds: Any, units: Any) -> List[COPContact]:
        """
        Update the COP with new sensor feeds and unit positions.

        Returns updated contacts.
        """
        # Add units
        for unit in units:
            self.units[unit.unit_id] = unit

        # Fuse sensor feeds
        fused = self._sensor_fusion.fuse_feeds(feeds)

        # Classify threats
        from ...data.entities import ThreatLevel
        blue_positions = [u.position for u in units if u.team == "blue"]

        for fused_contact in fused:
            contact = fused_contact.to_contact()
            threat_score = self._threat_classifier.classify(contact, blue_positions)

            if contact.contact_id in self.contacts:
                # Update existing
                existing = self.contacts[contact.contact_id]
                existing.contact = contact
                existing.threat_score = threat_score
                existing.last_seen = fused_contact.last_update
                existing.fusion_sources = len(fused_contact.source_feeds)
            else:
                # New contact
                self.contacts[contact.contact_id] = COPContact(
                    contact=contact,
                    threat_score=threat_score,
                    last_seen=fused_contact.last_update,
                    fusion_sources=len(fused_contact.source_feeds),
                )

        return list(self.contacts.values())

    def get_threatening_contacts(self, min_level: Optional[Any] = None) -> List[COPContact]:
        """Get all contacts at or above a threat level."""
        from ...data.entities import ThreatLevel
        min_level = min_level or ThreatLevel.MEDIUM
        threat_order = [ThreatLevel.UNKNOWN, ThreatLevel.LOW, ThreatLevel.MEDIUM,
                       ThreatLevel.HIGH, ThreatLevel.CRITICAL, ThreatLevel.IMMINENT]
        min_index = threat_order.index(min_level)

        return [
            c for c in self.contacts.values()
            if threat_order.index(c.contact.threat_level) >= min_index
        ]

    def get_contacts_by_domain(self, domain: Any) -> List[COPContact]:
        """Get contacts for a specific domain."""
        return [c for c in self.contacts.values() if c.contact.domain == domain]

    def get_contact(self, contact_id: str) -> Optional[COPContact]:
        """Get a specific contact."""
        return self.contacts.get(contact_id)

    def remove_stale_contacts(self, stale_threshold_ticks: int = 10) -> int:
        """Remove contacts not updated recently. Returns count removed."""
        # In simulation, would track last update tick
        # For now, placeholder
        return 0

    def get_cop_summary(self) -> str:
        """Get a human-readable COP summary."""
        from ...data.entities import DomainType, ThreatLevel
        lines = ["=" * 50, "🗺️ COMMON OPERATING PICTURE", "=" * 50]

        # Count by domain
        for domain in DomainType:
            count = len(self.get_contacts_by_domain(domain))
            if count > 0:
                lines.append(f"{domain.value.upper()}: {count} contacts")

        # High threat contacts
        high_threat = self.get_threatening_contacts(ThreatLevel.HIGH)
        if high_threat:
            lines.append("")
            lines.append("HIGH THREAT CONTACTS:")
            for contact in high_threat[:5]:
                lines.append(f"  - {contact.contact.contact_id}: Score {contact.threat_score.score:.1f}")

        lines.append("=" * 50)
        return "\n".join(lines)

    def get_stats(self) -> dict:
        from ...data.entities import DomainType, ThreatLevel
        return {
            "total_contacts": len(self.contacts),
            "units_tracked": len(self.units),
            "by_domain": {
                d.value: len(self.get_contacts_by_domain(d))
                for d in DomainType
            },
            "high_threat_count": len(self.get_threatening_contacts(ThreatLevel.HIGH)),
        }