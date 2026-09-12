# Copyright (c) Ultrone Contributors. All rights reserved.
"""Brain perception module - sensor processing and situational awareness."""

from __future__ import annotations

# Keep these as lazy imports to avoid circular dependency issues
__all__ = ["SensorFusion", "ThreatClassifier", "SituationalAwareness",
           "MultiSourceAnalyzer", "DataSourceType", "SensorDataPacket", "IntelligenceAssessment",
           "TerrainAnalyzer", "BattlefieldAnalyzer", "Battlefield3DExporter",
           "AwarenessEngine", "AwarenessEngineConfig", "AwarenessReport"]

def __getattr__(name: str):
    """Lazy import to avoid circular dependencies."""
    if name == "SensorFusion":
        from .sensor_fusion import SensorFusion
        return SensorFusion
    if name == "ThreatClassifier":
        from .threat_classifier import ThreatClassifier
        return ThreatClassifier
    if name == "SituationalAwareness":
        from .legacy_situational_awareness import SituationalAwareness
        return SituationalAwareness
    if name == "TerrainAnalyzer":
        from .terrain_analyzer import TerrainAnalyzer
        return TerrainAnalyzer
    if name == "BattlefieldAnalyzer":
        from .battlefield_analyzer import BattlefieldAnalyzer
        return BattlefieldAnalyzer
    if name == "Battlefield3DExporter":
        from .battlefield_3d import Battlefield3DExporter
        return Battlefield3DExporter
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
    if name == "AwarenessEngine":
        from .situational_awareness import AwarenessEngine
        return AwarenessEngine
    if name == "AwarenessEngineConfig":
        from .situational_awareness import AwarenessEngineConfig
        return AwarenessEngineConfig
    if name == "AwarenessReport":
        from .situational_awareness import AwarenessReport
        return AwarenessReport
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
