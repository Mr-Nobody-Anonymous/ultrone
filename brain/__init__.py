# Copyright (c) Ultrone Contributors. All rights reserved.
"""Brain module - central C2 and AI systems."""

from __future__ import annotations

# Import Orchestrator at module level - safe because it uses late imports internally
from .orchestrator import Orchestrator

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
    "CourseOfAction", "COAGenerator", "COAScorer", "Action",
    "ResourceAllocator", "Allocation",
    # Strategy
    "Doctrine", "ROE", "EngagementRules",
    "OperationalPlanner", "Mission",
    "StrategicPlanner", "StrategicObjective",
]

# Late imports to avoid circular dependencies
def __getattr__(name: str):
    """Lazy import of brain components to avoid circular imports."""
    if name == "Gene":
        from .learning.genome import Gene
        return Gene
    if name == "Capsule":
        from .learning.genome import Capsule
        return Capsule
    if name == "Genome":
        from .learning.genome import Genome
        return Genome
    if name == "GenomeEngine":
        from .learning.genome import GenomeEngine
        return GenomeEngine
    if name == "MutationStrategy":
        from .learning.genome import MutationStrategy
        return MutationStrategy
    if name == "CrossoverStrategy":
        from .learning.genome import CrossoverStrategy
        return CrossoverStrategy
    if name == "SelectionStrategy":
        from .learning.genome import SelectionStrategy
        return SelectionStrategy
    if name == "EvolutionLab":
        from .learning.evolution_lab import EvolutionLab
        return EvolutionLab
    if name == "EvolutionConfig":
        from .learning.evolution_lab import EvolutionConfig
        return EvolutionConfig
    if name == "TelemetryEvent":
        from .learning.performance_telemetry import TelemetryEvent
        return TelemetryEvent
    if name == "TelemetryMetrics":
        from .learning.performance_telemetry import TelemetryMetrics
        return TelemetryMetrics
    if name == "PerformanceTelemetry":
        from .learning.performance_telemetry import PerformanceTelemetry
        return PerformanceTelemetry
    if name == "EngagementHistory":
        from .learning.experience_memory import EngagementHistory
        return EngagementHistory
    if name == "ExperienceMemory":
        from .learning.experience_memory import ExperienceMemory
        return ExperienceMemory
    if name == "PatternRecognizer":
        from .learning.pattern_recognizer import PatternRecognizer
        return PatternRecognizer
    if name == "ThreatPattern":
        from .learning.pattern_recognizer import ThreatPattern
        return ThreatPattern
    if name == "PatternType":
        from .learning.pattern_recognizer import PatternType
        return PatternType
    if name == "SensorFusion":
        from .perception import SensorFusion
        return SensorFusion
    if name == "ThreatClassifier":
        from .perception import ThreatClassifier
        return ThreatClassifier
    if name == "SituationalAwareness":
        from .perception import SituationalAwareness
        return SituationalAwareness
    if name == "TacticalEngine":
        from .reasoning import TacticalEngine
        return TacticalEngine
    if name == "TacticalAssessment":
        from .reasoning import TacticalAssessment
        return TacticalAssessment
    if name == "KillChain":
        from .reasoning import KillChain
        return KillChain
    if name == "KillChainPhase":
        from .reasoning import KillChainPhase
        return KillChainPhase
    if name == "KillChainStateMachine":
        from .reasoning import KillChainStateMachine
        return KillChainStateMachine
    if name == "KillChainCapsule":
        from .reasoning import KillChainCapsule
        return KillChainCapsule
    if name == "ActiveEvolutionManager":
        from .reasoning import ActiveEvolutionManager
        return ActiveEvolutionManager
    if name == "CompositeKillChain":
        from .reasoning import CompositeKillChain
        return CompositeKillChain
    if name == "CompositePhase":
        from .reasoning import CompositePhase
        return CompositePhase
    if name == "DomainEngagement":
        from .reasoning import DomainEngagement
        return DomainEngagement
    if name == "CourseOfAction":
        from .reasoning import CourseOfAction
        return CourseOfAction
    if name == "COAGenerator":
        from .reasoning import COAGenerator
        return COAGenerator
    if name == "COAScorer":
        from .reasoning import COAScorer
        return COAScorer
    if name == "ResourceAllocator":
        from .reasoning import ResourceAllocator
        return ResourceAllocator
    if name == "Allocation":
        from .reasoning import Allocation
        return Allocation
    if name == "Doctrine":
        from .strategy import Doctrine
        return Doctrine
    if name == "OperationalPlanner":
        from .strategy import OperationalPlanner
        return OperationalPlanner
    if name == "Mission":
        from .strategy import Mission
        return Mission
    if name == "StrategicPlanner":
        from .strategy import StrategicPlanner
        return StrategicPlanner
    if name == "StrategicObjective":
        from .strategy import StrategicObjective
        return StrategicObjective
    if name == "ROE":
        from .strategy import ROE
        return ROE
    if name == "EngagementRules":
        from .strategy import EngagementRules
        return EngagementRules
    if name == "Action":
        from .reasoning.course_of_action import Action
        return Action
    if name == "EvolutionaryGenome":
        from .reasoning.evolutionary_coagen import EvolutionaryGenome
        return EvolutionaryGenome
    if name == "EvolutionaryCOAGenerator":
        from .reasoning.evolutionary_coagen import EvolutionaryCOAGenerator
        return EvolutionaryCOAGenerator
    if name == "AgentEvolver":
        from .learning.agent_evolver import AgentEvolver
        return AgentEvolver
    if name == "AgentPersonality":
        from .learning.agent_evolver import AgentPersonality
        return AgentPersonality
    if name == "EngagementOutcome":
        from .learning.experience_memory import EngagementOutcome
        return EngagementOutcome
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")