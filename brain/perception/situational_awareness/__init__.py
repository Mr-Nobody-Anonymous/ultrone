# Copyright (c) Ultrone Contributors. All rights reserved.
"""Situational Awareness System for the UltronE research platform.

Implements the three Endsley levels of situational awareness:

* **Level 1 (Perception)** -- multi-sensor ingestion, validation, fusion
* **Level 2 (Comprehension)** -- world model, scene graph, semantic map,
  threat assessment, anomaly detection, intent estimation
* **Level 3 (Projection)** -- trajectory prediction, event prediction,
  uncertainty propagation

The system is built on async-first, fully-typed, event-driven architecture
with dependency injection, plugin-ready protocols, and GPU-ready abstractions.
"""

from __future__ import annotations

from ..legacy_situational_awareness import SituationalAwareness
from .active_perception import ActivePerception, ActivePerceptionConfig, PerceptionAction
from .anomaly_detector import AnomalyDetector, AnomalyDetectorConfig
from .attention_manager import AttentionAllocation, AttentionManager, AttentionManagerConfig
from .awareness_engine import AwarenessEngine, AwarenessEngineConfig, AwarenessReport
from .belief_state import BeliefStateEstimator, BeliefUpdateError, kl_divergence
from .causal_reasoner import CausalLink, CausalReasoner, CausalReasonerConfig
from .change_detector import ChangeDetector, ChangeDetectorConfig
from .confidence_engine import ConfidenceConfig, ConfidenceEngine, ConfidenceReport
from .context_engine import ContextEngine, ContextEngineConfig, ContextSnapshot
from .dynamic_map import DynamicMap, DynamicMapConfig, MapCell
from .entity_tracker import AssociationResult, EntityTracker, EntityTrackerConfig, TrackQuality
from .event_predictor import EventPredictor, EventPredictorConfig, EventRule
from .events import (
    AnomalyDetected,
    AttentionRedirected,
    ChangeReported,
    ConfidenceUpdated,
    DistributedTransport,
    DomainEvent,
    EntityUpdated,
    EventBus,
    EventPriority,
    EventWaiter,
    HypothesisUpdated,
    ObservationReceived,
    PredictionGenerated,
    WorldStateChanged,
)
from .explainability import ExplainabilityConfig, ExplainabilityEngine, Explanation
from .hypothesis_manager import Hypothesis, HypothesisManager, HypothesisManagerConfig
from .information_gain import InformationGain, InformationGainEstimator
from .intent_estimator import IntentEstimate, IntentEstimator, IntentEstimatorConfig
from .object_memory import ObjectMemory, ObjectMemoryConfig, ObjectMemoryRecord
from .observation_history import ObservationHistory, ObservationHistoryConfig
from .observation_validation import (
    ObservationValidator,
    ValidationError,
    ValidationResult,
    ValidationRule,
)
from .scene_graph import SceneGraph, SceneGraphEdge, SceneGraphNode, SceneGraphStats
from .semantic_mapper import SemanticMap, SemanticMapConfig, SemanticRegion
from .sensor_fusion import (
    BayesianFusion,
    CovarianceIntersectionFusion,
    DempsterShaferFusion,
    ExtendedKalmanFusion,
    FusionError,
    FusionResult,
    FusionStrategy,
    NeuralFusion,
    ParticleFusion,
    SensorFusionEngine,
    UnscentedKalmanFusion,
)
from .sensor_registry import (
    SensorAdapter,
    SensorDescriptor,
    SensorRegistrationError,
    SensorRegistry,
    SensorSpecification,
)
from .telemetry import (
    PerformanceReport,
    PerformanceTelemetry,
    TelemetryRecord,
    async_timed,
    timed,
)
from .temporal_reasoner import (
    TemporalCorrelation,
    TemporalPattern,
    TemporalReasoner,
    TemporalReasonerConfig,
)
from .threat_assessor import ThreatAssessor, ThreatAssessorConfig, ThreatAssessment
from .trajectory_predictor import (
    TrajectoryPrediction,
    TrajectoryPredictor,
    TrajectoryPredictorConfig,
)
from .types import (
    AnomalyReport,
    AnomalySeverity,
    BeliefDistribution,
    BeliefDistributionType,
    BeliefUpdate,
    ChangeReport,
    ChangeType,
    CovarianceMatrix,
    Disposition,
    EntityCategory,
    EntityFilter,
    EntityID,
    EntityState,
    EntityType,
    EventForecast,
    EvidenceChain,
    EvidenceLink,
    HypothesisStatus,
    Observation,
    PredictedState,
    PredictionHorizon,
    Relationship,
    RelationshipType,
    ScenarioBranch,
    SensorMeasurement,
    SensorStatus,
    SensorType,
    ThreatLevel,
    TrackedEntity,
    Vector3,
    WorldSnapshot,
    utc_now,
)
from .uncertainty_engine import UncertaintyConfig, UncertaintyEngine, UncertaintyMetrics
from .uncertainty_propagation import (
    UncertaintyPropagator,
    UncertaintyPropagatorConfig,
    UncertaintyTrace,
)
from .visualization import VisualizationConfig, VisualizationEngine
from .world_model import EntityNotFoundError, WorldModel, WorldModelConfig
from .world_state_cache import WorldStateCache, WorldStateCacheConfig

__all__ = [
    # Core types
    "EntityID",
    "Vector3",
    "CovarianceMatrix",
    "BeliefDistribution",
    "BeliefDistributionType",
    "EntityState",
    "TrackedEntity",
    "Observation",
    "SensorMeasurement",
    "Relationship",
    "PredictedState",
    "EventForecast",
    "AnomalyReport",
    "AnomalySeverity",
    "ChangeReport",
    "ChangeType",
    "WorldSnapshot",
    "EvidenceChain",
    "EvidenceLink",
    "ScenarioBranch",
    "BeliefUpdate",
    "EntityFilter",
    "EntityCategory",
    "EntityType",
    "SensorType",
    "SensorStatus",
    "Disposition",
    "ThreatLevel",
    "HypothesisStatus",
    "PredictionHorizon",
    "RelationshipType",
    "utc_now",
    "SituationalAwareness",
    # Events
    "EventBus",
    "EventPriority",
    "DomainEvent",
    "ObservationReceived",
    "EntityUpdated",
    "WorldStateChanged",
    "PredictionGenerated",
    "AnomalyDetected",
    "ChangeReported",
    "HypothesisUpdated",
    "AttentionRedirected",
    "ConfidenceUpdated",
    "DistributedTransport",
    "EventWaiter",
    # Telemetry
    "PerformanceTelemetry",
    "PerformanceReport",
    "TelemetryRecord",
    "timed",
    "async_timed",
    # Level 1: Perception
    "SensorRegistry",
    "SensorSpecification",
    "SensorDescriptor",
    "SensorAdapter",
    "SensorRegistrationError",
    "ObservationValidator",
    "ValidationResult",
    "ValidationRule",
    "ValidationError",
    "EntityTracker",
    "EntityTrackerConfig",
    "TrackQuality",
    "AssociationResult",
    "ObservationHistory",
    "ObservationHistoryConfig",
    "SensorFusionEngine",
    "FusionResult",
    "FusionStrategy",
    "FusionError",
    "BayesianFusion",
    "ExtendedKalmanFusion",
    "UnscentedKalmanFusion",
    "ParticleFusion",
    "DempsterShaferFusion",
    "CovarianceIntersectionFusion",
    "NeuralFusion",
    "BeliefStateEstimator",
    "BeliefUpdateError",
    "kl_divergence",
    # Level 2: Comprehension
    "WorldModel",
    "WorldModelConfig",
    "EntityNotFoundError",
    "SceneGraph",
    "SceneGraphNode",
    "SceneGraphEdge",
    "SceneGraphStats",
    "SemanticMap",
    "SemanticMapConfig",
    "SemanticRegion",
    "DynamicMap",
    "DynamicMapConfig",
    "MapCell",
    "TemporalReasoner",
    "TemporalReasonerConfig",
    "TemporalPattern",
    "TemporalCorrelation",
    "CausalReasoner",
    "CausalReasonerConfig",
    "CausalLink",
    "ThreatAssessor",
    "ThreatAssessorConfig",
    "ThreatAssessment",
    "AnomalyDetector",
    "AnomalyDetectorConfig",
    "IntentEstimator",
    "IntentEstimatorConfig",
    "IntentEstimate",
    "ContextEngine",
    "ContextEngineConfig",
    "ContextSnapshot",
    "ConfidenceEngine",
    "ConfidenceConfig",
    "ConfidenceReport",
    "UncertaintyEngine",
    "UncertaintyConfig",
    "UncertaintyMetrics",
    "UncertaintyPropagator",
    "UncertaintyPropagatorConfig",
    "UncertaintyTrace",
    "ChangeDetector",
    "ChangeDetectorConfig",
    "HypothesisManager",
    "HypothesisManagerConfig",
    "Hypothesis",
    "ObjectMemory",
    "ObjectMemoryConfig",
    "ObjectMemoryRecord",
    # Level 3: Projection
    "TrajectoryPredictor",
    "TrajectoryPredictorConfig",
    "TrajectoryPrediction",
    "EventPredictor",
    "EventPredictorConfig",
    "EventRule",
    # Attention and active perception
    "AttentionManager",
    "AttentionManagerConfig",
    "AttentionAllocation",
    "InformationGainEstimator",
    "InformationGain",
    "ActivePerception",
    "ActivePerceptionConfig",
    "PerceptionAction",
    # Explainability and visualization
    "ExplainabilityEngine",
    "ExplainabilityConfig",
    "Explanation",
    "VisualizationEngine",
    "VisualizationConfig",
    # Cache
    "WorldStateCache",
    "WorldStateCacheConfig",
    # Engine
    "AwarenessEngine",
    "AwarenessEngineConfig",
    "AwarenessReport",
]