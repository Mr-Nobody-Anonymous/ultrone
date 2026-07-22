# Copyright (c) Ultrone Contributors. All rights reserved.
"""Brain perception module - sensor processing and situational awareness."""

from __future__ import annotations

# Keep these as lazy imports to avoid circular dependency issues
__all__ = ["SensorFusion", "ThreatClassifier", "SituationalAwareness",
           "MultiSourceAnalyzer", "DataSourceType", "SensorDataPacket", "IntelligenceAssessment"]

def __getattr__(name: str):
    """Lazy import to avoid circular dependencies."""
    if name == "SensorFusion":
        from .sensor_fusion import SensorFusion
        return SensorFusion
    if name == "ThreatClassifier":
        from .threat_classifier import ThreatClassifier
        return ThreatClassifier
    if name == "SituationalAwareness":
        from .situational_awareness import SituationalAwareness
        return SituationalAwareness
    if name == "MultiSourceAnalyzer":
        from .multi_source_analyzer import MultiSourceAnalyzer
        return MultiSourceAnalyzer
    if name == "DataSourceType":
        from .multi_source_analyzer import DataSourceType
        return DataSourceType
    if name == "SensorDataPacket":
        from .multi_source_analyzer import SensorDataPacket
        return SensorDataPacket
    if name == "IntelligenceAssessment":
        from .multi_source_analyzer import IntelligenceAssessment
        return IntelligenceAssessment
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")