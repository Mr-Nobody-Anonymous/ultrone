# Copyright (c) Ultrone Contributors. All rights reserved.
"""Sensor feed data models for battlefield simulation."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Tuple


class FeedType(Enum):
    """Types of sensor feeds."""
    RADAR = "radar"
    VISUAL = "visual"
    SIGINT = "sigint"
    CYBER = "cyber"
    SONAR = "sonar"
    PASSIVE = "passive"


@dataclass
class SensorFeed:
    """Base class for sensor detections."""
    feed_id: str
    sensor_type: FeedType
    position: Tuple[float, float, float]
    detection_time: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    confidence: float = 1.0
    range_meters: float = 0.0
    bearing_deg: float = 0.0
    metadata: Dict = field(default_factory=dict)
    
    def to_dict(self) -> dict:
        return {
            "feed_id": self.feed_id,
            "sensor_type": self.sensor_type.value,
            "position": {"x": self.position[0], "y": self.position[1], "z": self.position[2]},
            "confidence": self.confidence,
            "range_meters": self.range_meters,
            "bearing_deg": self.bearing_deg,
            "detection_time": self.detection_time,
            "metadata": self.metadata,
        }


@dataclass
class RadarFeed(SensorFeed):
    """Radar detection feed."""
    altitude_meters: float = 0.0
    speed_mps: float = 0.0
    heading_deg: float = 0.0
    rcs: float = 0.0  # Radar cross-section
    doppler_shift: float = 0.0
    
    def __init__(self, **kwargs):
        super().__init__(sensor_type=FeedType.RADAR, **kwargs)


@dataclass
class VisualFeed(SensorFeed):
    """Optical/visual detection feed."""
    magnification: float = 1.0
    thermal_signature: float = 0.0  # 0.0 no signature, 1.0 maximum
    visual_classification: str = "unknown"
    day_time: bool = True
    
    def __init__(self, **kwargs):
        super().__init__(sensor_type=FeedType.VISUAL, **kwargs)


@dataclass
class SigintFeed(SensorFeed):
    """Signals intelligence feed."""
    frequency_mhz: float = 0.0
    modulation: str = "unknown"
    signal_strength_dbm: float = -100.0
    emitter_type: str = "unknown"
    protocol_detected: str = "unknown"
    
    def __init__(self, **kwargs):
        super().__init__(sensor_type=FeedType.SIGINT, **kwargs)


@dataclass
class CyberFeed(SensorFeed):
    """Cyber intrusion detection feed."""
    attack_vector: str = "unknown"
    payload_type: str = "unknown"
    source_ip: str = "unknown"
    target_system: str = "unknown"
    threat_intel: Dict = field(default_factory=dict)
    
    def __init__(self, **kwargs):
        super().__init__(sensor_type=FeedType.CYBER, **kwargs)


@dataclass
class SonarFeed(SensorFeed):
    """Sonar detection feed for underwater."""
    depth_meters: float = 0.0
    tonnage_estimate: float = 0.0
    acoustic_signature: float = 0.0
    
    def __init__(self, **kwargs):
        super().__init__(sensor_type=FeedType.SONAR, **kwargs)