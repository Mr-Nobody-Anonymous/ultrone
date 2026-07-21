# Copyright (c) Ultrone Contributors. All rights reserved.
"""Brain module - central C2 and AI systems."""

from .orchestrator import Orchestrator
from .learning import (
    Gene, Capsule, Genome, GenomeEngine,
    MutationStrategy, CrossoverStrategy, SelectionStrategy,
    EvolutionLab, EvolutionConfig,
    AgentEvolver, AgentPersonality,
    TelemetryEvent, TelemetryMetrics, PerformanceTelemetry,
    EngagementHistory, ExperienceMemory, EngagementOutcome,
    PatternRecognizer, ThreatPattern, PatternType,
)
from .perception import SensorFusion, ThreatClassifier, SituationalAwareness
from .reasoning import (
    TacticalEngine, TacticalAssessment,
    KillChain, KillChainPhase, KillChainStateMachine,
    KillChainCapsule, ActiveEvolutionManager,
    CompositeKillChain, CompositePhase, DomainEngagement,
    CourseOfAction, COAGenerator, COAScorer,
    ResourceAllocator, Allocation,
)
from .strategy import (
    Doctrine, ROE, EngagementRules,
    OperationalPlanner, Mission,
    StrategicPlanner, StrategicObjective,
)

__all__ = [
    "Orchestrator",
    # Learning
    "Gene", "Capsule", "Genome", "GenomeEngine",
    "MutationStrategy", "CrossoverStrategy", "SelectionStrategy",
    "EvolutionLab", "EvolutionConfig",
    "AgentEvolver", "AgentPersonality",
    "TelemetryEvent", "TelemetryMetrics", "PerformanceTelemetry",
    "EngagementHistory", "ExperienceMemory", "EngagementOutcome",
    "PatternRecognizer", "ThreatPattern", "PatternType",
    # Perception
    "SensorFusion", "ThreatClassifier", "SituationalAwareness",
    # Reasoning
    "TacticalEngine", "TacticalAssessment",
    "KillChain", "KillChainPhase", "KillChainStateMachine",
    "KillChainCapsule", "ActiveEvolutionManager",
    "CompositeKillChain", "CompositePhase", "DomainEngagement",
    "CourseOfAction", "COAGenerator", "COAScorer",
    "ResourceAllocator", "Allocation",
    # Strategy
    "Doctrine", "ROE", "EngagementRules",
    "OperationalPlanner", "Mission",
    "StrategicPlanner", "StrategicObjective",
]
