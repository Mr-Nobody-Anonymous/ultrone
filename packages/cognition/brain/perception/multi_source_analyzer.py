# Copyright (c) Ultrone Contributors. All rights reserved.
"""Multi-modal sensor analyzer for all source types."""

from __future__ import annotations

import logging
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
import random

logger = logging.getLogger("Ultrone.Brain.Perception.MultiSourceAnalyzer")


class DataSourceType(Enum):
    """All possible sensor/communication sources."""
    SATELLITE_IMAGE = "satellite_image"
    RADAR = "radar"
    GPS = "gps"
    VOICE = "voice"
    SIGINT = "sigint"
    CYBER_FEED = "cyber_feed"
    SONAR = "sonar"
    VISUAL = "visual"
    IMAGING = "imaging"
    ACOUSTIC = "acoustic"
    THERMAL = "thermal"


@dataclass
class SensorDataPacket:
    """Container for any type of sensor data."""
    source_type: DataSourceType
    source_id: str
    timestamp: float
    position: Tuple[float, float, float]
    raw_data: Any
    confidence: float = 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class IntelligenceAssessment:
    """Analysis result from multi-sensor fusion."""
    target_id: str
    threat_score: float
    intent_classification: str
    recommended_action: str
    supporting_evidence: List[Tuple[DataSourceType, float]]
    uncertainty: float
    
    def to_dict(self) -> dict:
        return {
            "target_id": self.target_id,
            "threat_score": self.threat_score,
            "intent": self.intent_classification,
            "recommended_action": self.recommended_action,
            "evidence": [(e[0].value, e[1]) for e in self.supporting_evidence],
            "uncertainty": self.uncertainty,
        }


class MultiSourceAnalyzer:
    """Analyzes data from all sensor types using specialized AI for each data type."""
    
    INTENT_PATTERNS = {
        "aggression": ["high_speed", "toward_friendly", "weapon_signature"],
        "reconnaissance": ["slow_approach", "scanning", "relay_behavior"],
        "logistics": ["static", "supply_movement", "pattern_repeat"],
        "civilian": ["predictable_path", "no_weapon", "civilian_infrastructure"],
    }
    
    def __init__(self):
        # Lazy import specialized analyzers
        self._analysis_cache: Dict[str, IntelligenceAssessment] = {}
    
    def analyze(self, data_packets: List[SensorDataPacket]) -> List[IntelligenceAssessment]:
        """Analyze multi-source sensor data and produce intelligence assessments."""
        # Import specialized analyzers here to avoid circular imports
        from .specialized_analyzers import ANALYZER_REGISTRY
        
        grouped = self._group_packets_by_location(data_packets)
        
        assessments = []
        for location_key, packets in grouped.items():
            assessment = self._analyze_group(packets, ANALYZER_REGISTRY)
            if assessment:
                assessments.append(assessment)
                self._analysis_cache[assessment.target_id] = assessment
        
        return assessments
    
    def _group_packets_by_location(self, packets: List[SensorDataPacket], 
                                  tolerance_meters: float = 1000) -> Dict[str, List[SensorDataPacket]]:
        groups = {}
        used = set()
        
        for i, packet in enumerate(packets):
            if i in used:
                continue
            group = [packet]
            used.add(i)
            
            for j, other in enumerate(packets):
                if j in used:
                    continue
                dx = other.position[0] - packet.position[0]
                dy = other.position[1] - packet.position[1]
                dz = other.position[2] - packet.position[2]
                if (dx ** 2 + dy ** 2 + dz ** 2) ** 0.5 < tolerance_meters:
                    group.append(other)
                    used.add(j)
            
            pos = packet.position
            loc_key = f"{int(pos[0]/1000)}:{int(pos[1]/1000)}:{int(pos[2]/1000)}"
            groups[loc_key] = group
        
        return groups
    
    def _analyze_group(self, packets: List[SensorDataPacket], 
                      analyzer_registry: Dict[str, Any]) -> Optional[IntelligenceAssessment]:
        if not packets:
            return None
        
        source_counts = {}
        for packet in packets:
            st = packet.source_type
            source_counts[st] = source_counts.get(st, 0) + 1
        
        threat_score = self._calculate_threat_score(packets, source_counts, analyzer_registry)
        intent = self._classify_intent(packets)
        action = self._recommend_action(threat_score, intent, packets)
        uncertainty = self._calculate_uncertainty(packets, source_counts)
        
        evidence = [(packet.source_type, packet.confidence) for packet in packets]
        
        return IntelligenceAssessment(
            target_id=f"TARGET-{random.randint(100000, 999999)}",
            threat_score=threat_score,
            intent_classification=intent,
            recommended_action=action,
            supporting_evidence=evidence,
            uncertainty=uncertainty,
        )
    
    def _calculate_threat_score(self, packets: List[SensorDataPacket], 
                                source_counts: Dict[DataSourceType, int],
                                analyzer_registry: Dict[str, Any]) -> float:
        """Calculate threat score using specialized AI for each data type."""
        combined_threat = 0.0
        total_weight = 0.0
        
        for packet in packets:
            source_type = packet.source_type.value
            analyzer = analyzer_registry.get(source_type)
            
            if analyzer:
                # Use specialized AI for this data type
                analysis = analyzer.analyze(packet.raw_data, packet.metadata)
                threat = analysis.get("threat_indicator", 0.5)
                confidence = analysis.get("confidence", 0.8)
                
                combined_threat += threat * confidence * packet.confidence
                total_weight += confidence * packet.confidence
            else:
                # Generic fallback
                combined_threat += 0.5
                total_weight += 1.0
        
        if total_weight == 0:
            return 0.5
        
        return min(1.0, max(0.0, combined_threat / total_weight))
    
    def _classify_intent(self, packets: List[SensorDataPacket]) -> str:
        intent_scores = {intent: 0.0 for intent in self.INTENT_PATTERNS}
        
        for packet in packets:
            metadata = packet.metadata
            if metadata.get("speed", 0) > 100:
                intent_scores["aggression"] += 0.3
            if metadata.get("heading_toward_friendly", False):
                intent_scores["aggression"] += 0.4
            if metadata.get("pattern", "") == "grid_search":
                intent_scores["reconnaissance"] += 0.3
            if metadata.get("emitting", False):
                intent_scores["reconnaissance"] += 0.2
            if metadata.get("pattern", "") == "regular_intervals":
                intent_scores["logistics"] += 0.3
        
        if all(v == 0 for v in intent_scores.values()):
            return "unknown"
        
        return max(intent_scores, key=intent_scores.get)
    
    def _recommend_action(self, threat_score: float, intent: str,
                         packets: List[SensorDataPacket]) -> str:
        if threat_score > 0.8:
            return "engage_immediate"
        if intent == "aggression" and threat_score > 0.5:
            return "intercept"
        if intent == "reconnaissance":
            return "surveil"
        if intent == "logistics":
            return "monitor"
        if intent == "civilian":
            return "avoid"
        return "observe"
    
    def _calculate_uncertainty(self, packets: List[SensorDataPacket],
                                source_counts: Dict[DataSourceType, int]) -> float:
        diversity_factor = 1.0 - (len(source_counts) / len(DataSourceType))
        conflict_penalty = 0.0
        for i, p1 in enumerate(packets):
            for p2 in packets[i+1:]:
                dx = p1.position[0] - p2.position[0]
                dy = p1.position[1] - p2.position[1]
                dz = p1.position[2] - p2.position[2]
                dist = (dx**2 + dy**2 + dz**2) ** 0.5
                if dist > 500:
                    conflict_penalty += 0.1
        avg_confidence = sum(p.confidence for p in packets) / len(packets)
        return min(1.0, diversity_factor + conflict_penalty + (1 - avg_confidence))
    
    def get_analyses(self) -> List[IntelligenceAssessment]:
        return list(self._analysis_cache.values())
    
    def clear_cache(self) -> None:
        self._analysis_cache.clear()