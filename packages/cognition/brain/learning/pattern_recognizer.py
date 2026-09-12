# Copyright (c) Ultrone Contributors. All rights reserved.
"""Pattern recognition for enemy tactics and engagement analysis."""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Any
from enum import Enum
import random

from .experience_memory import ExperienceMemory, EngagementHistory

logger = logging.getLogger("Ultrone.Brain.Learning.PatternRecognizer")


class PatternType(Enum):
    """Types of recognized patterns."""
    TACTICAL = "tactical"      # Enemy tactics
    BEHAVIORAL = "behavioral"  # Movement patterns
    SIGNAL = "signal"          # SIGINT signatures
    TEMPORAL = "temporal"      # Timing patterns


@dataclass
class ThreatPattern:
    """A recognized pattern in enemy behavior."""
    pattern_id: str
    pattern_type: PatternType
    domain: str
    description: str
    confidence: float  # 0.0-1.0
    first_seen: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    last_seen: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    occurrences: int = 0
    indicators: List[str] = field(default_factory=list)  # What indicates this pattern
    countermeasures: List[str] = field(default_factory=list)
    
    def to_dict(self) -> dict:
        return {
            "pattern_id": self.pattern_id,
            "pattern_type": self.pattern_type.value,
            "domain": self.domain,
            "description": self.description,
            "confidence": self.confidence,
            "first_seen": self.first_seen,
            "last_seen": self.last_seen,
            "occurrences": self.occurrences,
            "indicators": self.indicators,
            "countermeasures": self.countermeasures,
        }


class PatternRecognizer:
    """
    Mines experience memory for enemy tactics patterns.
    
    Analyzes engagement history to identify recurring enemy behaviors
    and suggest countermeasures.
    """
    
    # Known pattern templates for simulation
    PATTERN_TEMPLATES = {
        "air_swarm": ThreatPattern(
            pattern_id="P-AIR-SWARM",
            pattern_type=PatternType.TACTICAL,
            domain="air",
            description="Coordinated drone swarm attack",
            confidence=0.9,
            indicators=["multiple contacts", "low altitude", "coordinated approach"],
            countermeasures=["electronic warfare", "shotgun pattern", "altitude advantage"],
        ),
        "cyber_probe": ThreatPattern(
            pattern_id="P-CYBER-PROBE",
            pattern_type=PatternType.SIGNAL,
            domain="cyber",
            description="Reconnaissance network probe",
            confidence=0.85,
            indicators=["port scanning", "low volume", "consistent intervals"],
            countermeasures=["honeypot", "IP blacklisting", "protocol obfuscation"],
        ),
        "naval_sub_run": ThreatPattern(
            pattern_id="P-NAVAL-SUB",
            pattern_type=PatternType.BEHAVIORAL,
            domain="sea",
            description="Submarine periscope exposure pattern",
            confidence=0.8,
            indicators=["sonar contact", "shallow depth", "brief exposure"],
            countermeasures=["rapid depth charge", "sonar array shift", "helicopter ASW"],
        ),
    }
    
    def __init__(self, experience_memory: Optional[ExperienceMemory] = None):
        self.experience = experience_memory or ExperienceMemory()
        self.recognized_patterns: Dict[str, ThreatPattern] = {}
    
    def analyze_engagements(self) -> List[ThreatPattern]:
        """Analyze all engagements to find patterns."""
        self.recognized_patterns.clear()
        
        for engagement in self.experience.engagements:
            patterns = self._find_patterns_in_engagement(engagement)
            for pattern in patterns:
                if pattern.pattern_id in self.recognized_patterns:
                    existing = self.recognized_patterns[pattern.pattern_id]
                    existing.occurrences += 1
                    existing.confidence = min(1.0, existing.confidence + 0.05)
                else:
                    self.recognized_patterns[pattern.pattern_id] = pattern
        
        return list(self.recognized_patterns.values())
    
    def _find_patterns_in_engagement(self, engagement: EngagementHistory) -> List[ThreatPattern]:
        """Find patterns in a single engagement."""
        patterns = []
        
        # Check against known templates based on domain
        for pid, template in self.PATTERN_TEMPLATES.items():
            if template.domain == engagement.domain:
                # Simulate pattern matching
                if random.random() < 0.1:  # 10% chance to identify
                    patterns.append(ThreatPattern(
                        pattern_id=f"{pid}-{random.randint(1000, 9999)}",
                        pattern_type=template.pattern_type,
                        domain=template.domain,
                        description=template.description,
                        confidence=0.7,
                        indicators=template.indicators,
                        countermeasures=template.countermeasures,
                    ))
        
        return patterns
    
    def get_pattern(self, pattern_id: str) -> Optional[ThreatPattern]:
        """Get a recognized pattern by ID."""
        return self.recognized_patterns.get(pattern_id)
    
    def detect_patterns_in_contacts(self, contacts: List[Any]) -> List[ThreatPattern]:
        """
        Detect patterns in real-time from threatening contacts.
        
        This is called during the Orient phase to identify enemy tactics
        that trigger immediate evolution.
        
        For active evolution: returns patterns with >80% confidence.
        """
        detected = []
        
        for contact in contacts:
            # Extract contact for analysis
            c = contact.contact if hasattr(contact, "contact") else contact
            
            # Check for pattern indicators in real-time
            indicators = self._extract_indicators(c)
            
            # Match against known pattern templates
            for pid, template in self.PATTERN_TEMPLATES.items():
                if template.domain == c.domain.value:
                    matches = sum(1 for i in indicators if i in template.indicators)
                    if matches >= len(template.indicators) * 0.5:  # 50% match threshold
                        # High confidence pattern detected!
                        detected.append(ThreatPattern(
                            pattern_id=f"{pid}-ACTIVE-{random.randint(1000, 9999)}",
                            pattern_type=template.pattern_type,
                            domain=template.domain,
                            description=template.description,
                            confidence=min(0.95, template.confidence + (matches / len(template.indicators) * 0.1)),
                            indicators=template.indicators,
                            countermeasures=template.countermeasures,
                        ))
        
        return detected
    
    def _extract_indicators(self, contact: Any) -> List[str]:
        """Extract tactical indicators from a contact for pattern matching."""
        indicators = []
        
        domain = contact.domain.value if hasattr(contact, "domain") else "unknown"
        
        if domain == "air":
            if contact.speed < 50:
                indicators.append("low altitude")
            if len(contact.capabilities) > 3:
                indicators.append("multiple contacts")
        elif domain == "sea":
            if hasattr(contact, "altitude") and contact.altitude < 50:
                indicators.append("shallow depth")
        elif domain == "cyber":
            if contact.speed < 100:
                indicators.append("low volume")
        
        return indicators
    
    def get_patterns_by_domain(self, domain: str) -> List[ThreatPattern]:
        """Get all patterns for a domain."""
        return [p for p in self.recognized_patterns.values() if p.domain == domain]
    
    def suggest_countermeasures(self, domain: str, threat_indicators: List[str]) -> List[str]:
        """Suggest countermeasures based on threat indicators."""
        suggestions = []
        
        for pattern in self.recognized_patterns.values():
            if pattern.domain == domain:
                # Check if indicators match
                matches = sum(1 for i in threat_indicators if i in pattern.indicators)
                if matches >= len(threat_indicators) * 0.5:  # 50% match threshold
                    suggestions.extend(pattern.countermeasures)
        
        return list(set(suggestions))  # Unique
    
    def get_stats(self) -> dict:
        return {
            "patterns_recognized": len(self.recognized_patterns),
            "engagements_analyzed": len(self.experience.engagements),
            "patterns_by_domain": {
                d: len(self.get_patterns_by_domain(d))
                for d in ["air", "land", "sea", "cyber", "space"]
            },
        }