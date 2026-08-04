# Copyright (c) Ultrone Contributors. All rights reserved.
"""Core data types for the ULTRONE cognitive architecture.

These types flow through the cognitive loop and are consumed/produced by
every cognitive layer. They are designed to be serializable and versionable
so that full decision traces can be persisted and audited.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


# ── Modality ──────────────────────────────────────────────────────────────────

class Modality(Enum):
    """Sensory modalities that can be perceived."""
    VISION = "vision"
    AUDIO = "audio"
    TEXT = "text"
    TELEMETRY = "telemetry"
    GRAPH = "graph"
    GEOSPATIAL = "geospatial"
    TIME_SERIES = "time_series"
    STRUCTURED_DB = "structured_db"
    UNKNOWN = "unknown"


class UncertaintyType(Enum):
    """Types of uncertainty that can be tracked."""
    EPISTEMIC = "epistemic"       # Model uncertainty
    ALEATORIC = "aleatoric"       # Data noise
    DISTRIBUTION_SHIFT = "distribution_shift"
    SENSOR_DISAGREEMENT = "sensor_disagreement"
    MEMORY_CORRUPTION = "memory_corruption"


class PlanningHorizon(Enum):
    """Planning time horizons."""
    REACTIVE = "reactive"         # Immediate, reflexive
    TACTICAL = "tactical"         # Short-term (minutes to hours)
    OPERATIONAL = "operational"   # Medium-term (hours to days)
    STRATEGIC = "strategic"       # Long-term (days to months)


class ReasoningStrategy(Enum):
    """Multi-strategy reasoning methods."""
    DEDUCTIVE = "deductive"
    INDUCTIVE = "inductive"
    ABDUCTIVE = "abductive"
    ANALOGICAL = "analogical"
    PROBABILISTIC = "probabilistic"
    CAUSAL = "causal"
    COUNTERFACTUAL = "counterfactual"
    TEMPORAL = "temporal"
    SPATIAL = "spatial"
    CONSTRAINT_BASED = "constraint_based"
    GRAPH_REASONING = "graph_reasoning"
    NEURO_SYMBOLIC = "neuro_symbolic"


class PlannerType(Enum):
    """Available planning algorithms."""
    BEHAVIOR_TREE = "behavior_tree"
    HTN = "htn"
    GOAP = "goap"
    UTILITY_AI = "utility_ai"
    MCTS = "mcts"
    CONSTRAINT_OPTIMIZATION = "constraint_optimization"
    MODEL_PREDICTIVE_CONTROL = "mpc"
    MULTI_AGENT_PLANNING = "multi_agent_planning"
    HIERARCHICAL = "hierarchical"
    REACTIVE = "reactive"


# ── Perception Types ──────────────────────────────────────────────────────────

@dataclass
class Observation:
    """A multimodal observation from the environment.

    Fuses observations from all perceptual modalities into a unified
    observation with uncertainty estimates.
    """
    observation_id: str = field(default_factory=lambda: f"obs-{uuid.uuid4().hex[:12]}")
    timestamp: float = field(default_factory=time.time)
    modalities: Dict[Modality, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    source: str = "environment"
    confidence: float = 1.0
    uncertainty: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "observation_id": self.observation_id,
            "timestamp": self.timestamp,
            "modalities": {k.value: v for k, v in self.modalities.items()},
            "metadata": self.metadata,
            "source": self.source,
            "confidence": self.confidence,
            "uncertainty": self.uncertainty,
        }


@dataclass
class SceneGraphNode:
    """A node in the probabilistic scene graph."""
    node_id: str
    label: str
    entity_type: str
    properties: Dict[str, Any] = field(default_factory=dict)
    confidence: float = 1.0
    uncertainty: float = 0.0
    temporal_bounds: Tuple[float, float] = field(default_factory=lambda: (time.time(), float('inf')))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "node_id": self.node_id,
            "label": self.label,
            "entity_type": self.entity_type,
            "properties": self.properties,
            "confidence": self.confidence,
            "uncertainty": self.uncertainty,
            "temporal_bounds": list(self.temporal_bounds),
        }


@dataclass
class SceneGraphEdge:
    """An edge in the probabilistic scene graph representing relationships."""
    source_id: str
    target_id: str
    relationship_type: str
    confidence: float = 1.0
    weight: float = 1.0
    properties: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "source_id": self.source_id,
            "target_id": self.target_id,
            "relationship_type": self.relationship_type,
            "confidence": self.confidence,
            "weight": self.weight,
            "properties": self.properties,
        }


@dataclass
class SceneGraph:
    """A unified probabilistic scene graph fusing all modalities."""
    graph_id: str = field(default_factory=lambda: f"sg-{uuid.uuid4().hex[:12]}")
    nodes: List[SceneGraphNode] = field(default_factory=list)
    edges: List[SceneGraphEdge] = field(default_factory=list)
    timestamp: float = field(default_factory=time.time)
    overall_confidence: float = 0.0
    uncertainty_estimate: 'UncertaintyEstimate' = field(default_factory=lambda: UncertaintyEstimate())
    metadata: Dict[str, Any] = field(default_factory=dict)

    def add_node(self, node: SceneGraphNode) -> None:
        self.nodes.append(node)

    def add_edge(self, edge: SceneGraphEdge) -> None:
        self.edges.append(edge)

    def get_node(self, node_id: str) -> Optional[SceneGraphNode]:
        for n in self.nodes:
            if n.node_id == node_id:
                return n
        return None

    def find_nodes(self, label: str = None, entity_type: str = None) -> List[SceneGraphNode]:
        results = []
        for n in self.nodes:
            if label and n.label != label:
                continue
            if entity_type and n.entity_type != entity_type:
                continue
            results.append(n)
        return results

    def get_neighbors(self, node_id: str) -> List[SceneGraphNode]:
        neighbor_ids = set()
        for e in self.edges:
            if e.source_id == node_id:
                neighbor_ids.add(e.target_id)
            elif e.target_id == node_id:
                neighbor_ids.add(e.source_id)
        return [n for n in self.nodes if n.node_id in neighbor_ids]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "graph_id": self.graph_id,
            "nodes": [n.to_dict() for n in self.nodes],
            "edges": [e.to_dict() for e in self.edges],
            "timestamp": self.timestamp,
            "overall_confidence": self.overall_confidence,
            "uncertainty_estimate": self.uncertainty_estimate.to_dict(),
            "metadata": self.metadata,
        }


@dataclass
class UncertaintyEstimate:
    """Quantified uncertainty for an observation or decision."""
    epistemic: float = 0.0
    aleatoric: float = 0.0
    total: float = 0.0
    type: UncertaintyType = UncertaintyType.EPISTEMIC
    contributing_factors: List[str] = field(default_factory=list)
    confidence_intervals: Dict[str, Tuple[float, float]] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "epistemic": self.epistemic,
            "aleatoric": self.aleatoric,
            "total": self.total,
            "type": self.type.value,
            "contributing_factors": self.contributing_factors,
            "confidence_intervals": {
                k: list(v) for k, v in self.confidence_intervals.items()
            },
        }


# ── Situational Awareness Types ───────────────────────────────────────────────

@dataclass
class SituationalContext:
    """Continuously updated representation of the environment.

    Contains: entities, relationships, temporal events, environmental conditions,
    confidence, unknown regions, and prediction horizon.
    """
    context_id: str = field(default_factory=lambda: f"ctx-{uuid.uuid4().hex[:12]}")
    timestamp: float = field(default_factory=time.time)
    entities: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    relationships: List[Dict[str, Any]] = field(default_factory=list)
    temporal_events: List[Dict[str, Any]] = field(default_factory=list)
    environmental_conditions: Dict[str, Any] = field(default_factory=dict)
    confidence: float = 1.0
    unknown_regions: List[Dict[str, Any]] = field(default_factory=list)
    prediction_horizon: float = 300.0  # seconds
    scene_graph: Optional[SceneGraph] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        d = {
            "context_id": self.context_id,
            "timestamp": self.timestamp,
            "entities": self.entities,
            "relationships": self.relationships,
            "temporal_events": self.temporal_events,
            "environmental_conditions": self.environmental_conditions,
            "confidence": self.confidence,
            "unknown_regions": self.unknown_regions,
            "prediction_horizon": self.prediction_horizon,
            "metadata": self.metadata,
        }
        if self.scene_graph:
            d["scene_graph"] = self.scene_graph.to_dict()
        return d


# ── World Model Types ─────────────────────────────────────────────────────────

@dataclass
class WorldState:
    """Snapshot of the world state at a point in time."""
    state_id: str = field(default_factory=lambda: f"ws-{uuid.uuid4().hex[:12]}")
    timestamp: float = field(default_factory=time.time)
    entities: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    dynamics: Dict[str, Any] = field(default_factory=dict)
    resources: Dict[str, Any] = field(default_factory=dict)
    time_info: Dict[str, Any] = field(default_factory=dict)
    space_info: Dict[str, Any] = field(default_factory=dict)
    causal_structure: Dict[str, Any] = field(default_factory=dict)
    uncertainty: UncertaintyEstimate = field(default_factory=lambda: UncertaintyEstimate())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "state_id": self.state_id,
            "timestamp": self.timestamp,
            "entities": self.entities,
            "dynamics": self.dynamics,
            "resources": self.resources,
            "time": self.time_info,
            "space": self.space_info,
            "causal_structure": self.causal_structure,
            "uncertainty": self.uncertainty.to_dict(),
        }


@dataclass
class FuturePrediction:
    """A prediction of a future state or outcome."""
    prediction_id: str = field(default_factory=lambda: f"fp-{uuid.uuid4().hex[:12]}")
    horizon: float = 0.0  # time horizon in seconds
    scenario: str = "baseline"
    world_state: WorldState = field(default_factory=WorldState)
    confidence: float = 0.0
    uncertainty: UncertaintyEstimate = field(default_factory=lambda: UncertaintyEstimate())
    is_counterfactual: bool = False
    intervention: Optional[Dict[str, Any]] = None
    probability: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "prediction_id": self.prediction_id,
            "horizon": self.horizon,
            "scenario": self.scenario,
            "world_state": self.world_state.to_dict(),
            "confidence": self.confidence,
            "uncertainty": self.uncertainty.to_dict(),
            "is_counterfactual": self.is_counterfactual,
            "intervention": self.intervention,
            "probability": self.probability,
        }


# ── Memory Types ──────────────────────────────────────────────────────────────

class MemoryLayer(Enum):
    """Multi-tier memory systems."""
    WORKING = "working"
    EPISODIC = "episodic"
    SEMANTIC = "semantic"
    PROCEDURAL = "procedural"
    ASSOCIATIVE = "associative"
    VECTOR = "vector"
    GRAPH = "graph"


@dataclass
class MemoryItem:
    """A single item in cognitive memory."""
    item_id: str = field(default_factory=lambda: f"mem-{uuid.uuid4().hex[:12]}")
    layer: MemoryLayer = MemoryLayer.WORKING
    content: Any = None
    importance: float = 0.5
    timestamp: float = field(default_factory=time.time)
    access_count: int = 0
    last_accessed: float = field(default_factory=time.time)
    confidence: float = 1.0
    uncertainty: float = 0.0
    provenance: Dict[str, Any] = field(default_factory=dict)
    embedding: Optional[List[float]] = None
    related_items: List[str] = field(default_factory=list)


@dataclass
class MemoryRetrieval:
    """Result of a memory retrieval operation."""
    query: str
    results: List[MemoryItem] = field(default_factory=list)
    total_found: int = 0
    retrieval_time: float = 0.0
    method: str = ""
    confidence: float = 0.0


# ── Cognitive Context ─────────────────────────────────────────────────────────

@dataclass
class CognitiveContext:
    """Context that flows through the cognitive loop.

    Contains the current state, goals, constraints, and metadata.
    """
    context_id: str = field(default_factory=lambda: f"cog-{uuid.uuid4().hex[:12]}")
    goals: List[str] = field(default_factory=list)
    constraints: Dict[str, Any] = field(default_factory=dict)
    resources: Dict[str, float] = field(default_factory=dict)
    time_horizon: float = 300.0
    preferences: Dict[str, Any] = field(default_factory=dict)
    session_id: str = field(default_factory=lambda: f"sess-{uuid.uuid4().hex[:12]}")
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "context_id": self.context_id,
            "goals": self.goals,
            "constraints": self.constraints,
            "resources": self.resources,
            "time_horizon": self.time_horizon,
            "preferences": self.preferences,
            "session_id": self.session_id,
            "metadata": self.metadata,
            "timestamp": self.timestamp,
        }


# ── Action Types ──────────────────────────────────────────────────────────────

@dataclass
class Action:
    """An action selected by the cognitive system."""
    action_id: str = field(default_factory=lambda: f"act-{uuid.uuid4().hex[:12]}")
    name: str = ""
    parameters: Dict[str, Any] = field(default_factory=dict)
    priority: float = 0.0
    confidence: float = 1.0
    urgency: float = 0.5
    horizon: PlanningHorizon = PlanningHorizon.TACTICAL
    expected_utility: float = 0.0
    risk: float = 0.0
    source: str = "cognitive_agent"
    timestamp: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "action_id": self.action_id,
            "name": self.name,
            "parameters": self.parameters,
            "priority": self.priority,
            "confidence": self.confidence,
            "urgency": self.urgency,
            "horizon": self.horizon.value,
            "expected_utility": self.expected_utility,
            "risk": self.risk,
            "source": self.source,
            "timestamp": self.timestamp,
            "metadata": self.metadata,
        }


@dataclass
class ActionOutcome:
    """Observation of an action's outcome."""
    action_id: str
    success: bool
    actual_effect: Dict[str, Any] = field(default_factory=dict)
    reward: float = 0.0
    timestamp: float = field(default_factory=time.time)
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


# ── Prediction Types ─────────────────────────────────────────────────────────

@dataclass
class PredictionResult:
    """Result of ensemble prediction."""
    prediction_id: str = field(default_factory=lambda: f"pred-{uuid.uuid4().hex[:12]}")
    model_name: str = ""
    predictions: Dict[str, float] = field(default_factory=dict)
    confidence_intervals: Dict[str, Tuple[float, float]] = field(default_factory=dict)
    ensemble_weights: Dict[str, float] = field(default_factory=dict)
    feature_importance: Dict[str, float] = field(default_factory=dict)
    uncertainty: UncertaintyEstimate = field(default_factory=lambda: UncertaintyEstimate())
    timestamp: float = field(default_factory=time.time)
    model_version: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "prediction_id": self.prediction_id,
            "model_name": self.model_name,
            "predictions": self.predictions,
            "confidence_intervals": {
                k: list(v) for k, v in self.confidence_intervals.items()
            },
            "ensemble_weights": self.ensemble_weights,
            "feature_importance": self.feature_importance,
            "uncertainty": self.uncertainty.to_dict(),
            "timestamp": self.timestamp,
            "model_version": self.model_version,
        }


# ── Planning Types ───────────────────────────────────────────────────────────

@dataclass
class PlanStep:
    """A single step in a plan."""
    step_id: str
    action: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    preconditions: List[str] = field(default_factory=list)
    effects: List[str] = field(default_factory=list)
    duration: float = 0.0
    resource_cost: Dict[str, float] = field(default_factory=dict)
    confidence: float = 1.0
    risk: float = 0.0
    horizon: PlanningHorizon = PlanningHorizon.TACTICAL
    dependencies: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Plan:
    """A plan composed of ordered steps."""
    plan_id: str = field(default_factory=lambda: f"plan-{uuid.uuid4().hex[:12]}")
    goal: str = ""
    steps: List[PlanStep] = field(default_factory=list)
    planner_type: PlannerType = PlannerType.GOAP
    confidence: float = 0.0
    expected_utility: float = 0.0
    resource_cost: Dict[str, float] = field(default_factory=dict)
    horizon: PlanningHorizon = PlanningHorizon.TACTICAL
    alternatives: List['Plan'] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "plan_id": self.plan_id,
            "goal": self.goal,
            "steps": [
                {
                    "step_id": s.step_id,
                    "action": s.action,
                    "parameters": s.parameters,
                    "preconditions": s.preconditions,
                    "effects": s.effects,
                    "duration": s.duration,
                    "resource_cost": s.resource_cost,
                    "confidence": s.confidence,
                    "risk": s.risk,
                    "horizon": s.horizon.value,
                    "dependencies": s.dependencies,
                    "metadata": s.metadata,
                }
                for s in self.steps
            ],
            "planner_type": self.planner_type.value,
            "confidence": self.confidence,
            "expected_utility": self.expected_utility,
            "resource_cost": self.resource_cost,
            "horizon": self.horizon.value,
            "alternatives_count": len(self.alternatives),
            "metadata": self.metadata,
            "created_at": self.created_at,
        }


# ── Explainability Types ─────────────────────────────────────────────────────

@dataclass
class Evidence:
    """A piece of evidence supporting a decision."""
    evidence_id: str = field(default_factory=lambda: f"ev-{uuid.uuid4().hex[:12]}")
    source: str = ""
    description: str = ""
    confidence: float = 1.0
    weight: float = 1.0
    timestamp: float = field(default_factory=time.time)
    type: str = "observation"
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AlternativeOption:
    """An alternative option that was considered but not selected."""
    option_id: str = field(default_factory=lambda: f"alt-{uuid.uuid4().hex[:12]}")
    description: str = ""
    value: float = 0.0
    confidence: float = 0.0
    reason_rejected: str = ""


@dataclass
class MemoryReference:
    """Reference to a memory item that supported a decision."""
    memory_id: str
    layer: str
    relevance_score: float = 0.0
    content_snippet: str = ""


@dataclass
class CounterfactualExplanation:
    """Counterfactual explanation of a decision."""
    condition: str
    hypothesis: str
    estimated_effect: float
    confidence: float = 0.0
    intervention: Optional[Dict[str, Any]] = None


@dataclass
class DecisionTrace:
    """Full trace of a decision for explainability.

    Every decision must produce: decision trace, evidence, confidence,
    alternative options, counterfactual explanation, reasoning graph,
    feature importance, and supporting memory references.
    """
    trace_id: str = field(default_factory=lambda: f"trace-{uuid.uuid4().hex[:12]}")
    decision: str = ""
    timestamp: float = field(default_factory=time.time)
    context: Dict[str, Any] = field(default_factory=dict)
    evidence: List[Evidence] = field(default_factory=list)
    confidence: float = 0.0
    uncertainty: UncertaintyEstimate = field(default_factory=lambda: UncertaintyEstimate())
    alternative_options: List[AlternativeOption] = field(default_factory=list)
    counterfactual: Optional[CounterfactualExplanation] = None
    reasoning_strategy: ReasoningStrategy = ReasoningStrategy.DEDUCTIVE
    feature_importance: Dict[str, float] = field(default_factory=dict)
    supporting_memory: List[MemoryReference] = field(default_factory=list)
    reasoning_steps: List[str] = field(default_factory=list)
    cycle_phase: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def add_evidence(self, evidence: Evidence) -> None:
        self.evidence.append(evidence)

    def add_alternative(self, alt: AlternativeOption) -> None:
        self.alternative_options.append(alt)

    def add_memory_reference(self, ref: MemoryReference) -> None:
        self.supporting_memory.append(ref)

    def to_dict(self) -> Dict[str, Any]:
        d = {
            "trace_id": self.trace_id,
            "decision": self.decision,
            "timestamp": self.timestamp,
            "context": self.context,
            "evidence": [e.__dict__ if hasattr(e, '__dict__') else str(e) for e in self.evidence],
            "confidence": self.confidence,
            "uncertainty": self.uncertainty.to_dict(),
            "alternative_options": [
                {
                    "option_id": a.option_id,
                    "description": a.description,
                    "value": a.value,
                    "confidence": a.confidence,
                    "reason_rejected": a.reason_rejected,
                }
                for a in self.alternative_options
            ],
            "counterfactual": (
                {
                    "condition": self.counterfactual.condition,
                    "hypothesis": self.counterfactual.hypothesis,
                    "estimated_effect": self.counterfactual.estimated_effect,
                    "confidence": self.counterfactual.confidence,
                    "intervention": self.counterfactual.intervention,
                }
                if self.counterfactual else None
            ),
            "reasoning_strategy": self.reasoning_strategy.value,
            "feature_importance": self.feature_importance,
            "supporting_memory": [
                {
                    "memory_id": m.memory_id,
                    "layer": m.layer,
                    "relevance_score": m.relevance_score,
                    "content_snippet": m.content_snippet,
                }
                for m in self.supporting_memory
            ],
            "reasoning_steps": self.reasoning_steps,
            "cycle_phase": self.cycle_phase,
            "metadata": self.metadata,
        }
        return d


@dataclass
class ConfidenceCalibration:
    """Calibration of confidence estimates."""
    raw_confidence: float = 0.0
    calibrated_confidence: float = 0.0
    calibration_method: str = "platt_scaling"
    confidence_intervals: Dict[str, Tuple[float, float]] = field(default_factory=dict)
    calibration_history: List[Dict[str, Any]] = field(default_factory=list)
