# Copyright (c) Ultrone Contributors. All rights reserved.
"""ULTRONE Cognitive Architecture — unified cognitive orchestration layer.

Integrates perception, memory, world modeling, causal reasoning, planning,
prediction, continual learning, and self-reflection into a unified system.

Design Principles
-----------------
- **Modular**: Every cognitive layer is a pluggable module with a standard interface.
- **Event-driven**: All layers communicate via an internal event bus.
- **Self-organizing**: The cognitive loop adapts its own structure through meta-learning.
- **Continually learning**: Every cycle feeds experience back into memory and learning.
- **Explainable**: Every decision produces a full trace with evidence, confidence,
  alternative options, and counterfactuals.
- **Memory-centric**: All cognition is grounded in multi-tier memory systems.
- **Probabilistic**: Uncertainty is tracked and propagated throughout.
- **Causal**: Causal reasoning and counterfactuals are first-class citizens.
- **Hierarchical**: Decisions are made at reactive, tactical, operational, and strategic levels.
- **Resource-aware**: Planning accounts for computational and real-world resource constraints.
- **Fault tolerant**: Safety monitors continuously check for anomalies and trigger fallbacks.
- **Distributed**: Agents collaborate via blackboard, consensus, and message passing.
- **Extensible**: Plugin system for custom perception, reasoning, planning, and learning modules.
- **Benchmarkable**: Every cognitive cycle is instrumented for evaluation.
- **Human-supervised**: Safety monitors can request human review at any point.
"""

from __future__ import annotations

from .types import (
    Observation,
    Action,
    SceneGraph,
    SceneGraphNode,
    SceneGraphEdge,
    UncertaintyEstimate,
    CognitiveContext,
    PredictionResult,
    Plan,
    PlanStep,
    DecisionTrace,
    Evidence,
    AlternativeOption,
    CounterfactualExplanation,
    ConfidenceCalibration,
    MemoryReference,
)
from .event_types import (
    CognitiveEvent,
    CognitiveEventType,
    EventBus,
    PerceptionEvent,
    WorldModelUpdateEvent,
    MemoryRetrievalEvent,
    ReasoningEvent,
    PlanningEvent,
    ActionExecutionEvent,
    LearningEvent,
    SelfReflectionEvent,
    MetaLearningEvent,
    SafetyEvent,
)
from .exceptions import (
    CognitiveError,
    PerceptionError,
    WorldModelError,
    ReasoningError,
    PlanningError,
    MemoryError,
    SafetyError,
    UncertaintyError,
)
from .cycle_context import CycleContext, CyclePhase, PhaseResult
from .cognitive_loop import CognitiveLoop, CognitiveLoopConfig
from .cognitive_agent import CognitiveAgent, CognitiveAgentConfig

# Cognitive layer imports (lazy to avoid heavy dependencies at import time)
from .perception_layer import PerceptionLayer, PerceptionLayerConfig
from .situational_awareness_layer import SituationalAwarenessLayer, SituationalAwarenessConfig
from .world_model_layer import WorldModelLayer, WorldModelLayerConfig
from .active_inference_layer import ActiveInferenceLayer, ActiveInferenceConfig
from .memory_layer import MemoryLayer, MemoryLayerConfig
from .knowledge_layer import KnowledgeLayer, KnowledgeLayerConfig
from .reasoning_layer import ReasoningLayer, ReasoningLayerConfig
from .planning_layer import PlanningLayer, PlanningLayerConfig
from .prediction_layer import PredictionLayer, PredictionLayerConfig
from .self_reflection_layer import SelfReflectionLayer, SelfReflectionConfig
from .meta_learning_layer import MetaLearningLayer, MetaLearningConfig
from .agentic_layer import AgenticLayer, AgenticLayerConfig
from .learning_layer import LearningLayer, LearningLayerConfig
from .explainability_layer import ExplainabilityLayer, ExplainabilityLayerConfig
from .safety_layer import SafetyLayer, SafetyLayerConfig

__all__ = [
    # Types
    "Observation",
    "Action",
    "SceneGraph",
    "SceneGraphNode",
    "SceneGraphEdge",
    "UncertaintyEstimate",
    "CognitiveContext",
    "PredictionResult",
    "Plan",
    "PlanStep",
    "DecisionTrace",
    "Evidence",
    "AlternativeOption",
    "CounterfactualExplanation",
    "ConfidenceCalibration",
    "MemoryReference",
    # Events
    "CognitiveEvent",
    "CognitiveEventType",
    "EventBus",
    "PerceptionEvent",
    "WorldModelUpdateEvent",
    "MemoryRetrievalEvent",
    "ReasoningEvent",
    "PlanningEvent",
    "ActionExecutionEvent",
    "LearningEvent",
    "SelfReflectionEvent",
    "MetaLearningEvent",
    "SafetyEvent",
    # Exceptions
    "CognitiveError",
    "PerceptionError",
    "WorldModelError",
    "ReasoningError",
    "PlanningError",
    "MemoryError",
    "SafetyError",
    "UncertaintyError",
    # Core
    "CycleContext",
    "CyclePhase",
    "PhaseResult",
    "CognitiveLoop",
    "CognitiveLoopConfig",
    "CognitiveAgent",
    "CognitiveAgentConfig",
    # Layers
    "PerceptionLayer",
    "PerceptionLayerConfig",
    "SituationalAwarenessLayer",
    "SituationalAwarenessConfig",
    "WorldModelLayer",
    "WorldModelLayerConfig",
    "ActiveInferenceLayer",
    "ActiveInferenceConfig",
    "MemoryLayer",
    "MemoryLayerConfig",
    "KnowledgeLayer",
    "KnowledgeLayerConfig",
    "ReasoningLayer",
    "ReasoningLayerConfig",
    "PlanningLayer",
    "PlanningLayerConfig",
    "PredictionLayer",
    "PredictionLayerConfig",
    "SelfReflectionLayer",
    "SelfReflectionConfig",
    "MetaLearningLayer",
    "MetaLearningConfig",
    "AgenticLayer",
    "AgenticLayerConfig",
    "LearningLayer",
    "LearningLayerConfig",
    "ExplainabilityLayer",
    "ExplainabilityLayerConfig",
    "SafetyLayer",
    "SafetyLayerConfig",
]
