# Copyright (c) Ultrone Contributors. All rights reserved.
"""Core primitive types for the situational awareness system.

This module defines the foundational data models shared across the entire
situational awareness subsystem. Every other module imports from here, so this
module must remain free of any intra-package imports to guarantee there are no
circular dependency chains.

The type system models the three Endsley levels:

* **Level 1 (Perception)**  -- :class:`Observation`, :class:`SensorMeasurement`
* **Level 2 (Comprehension)** -- :class:`EntityState`, :class:`Relationship`,
  :class:`TrackedEntity`, :class:`WorldSnapshot`
* **Level 3 (Projection)** -- :class:`PredictedState`, :class:`EventForecast`,
  :class:`ScenarioBranch`
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field as dc_field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, Generic, List, Mapping, Optional, Sequence, Tuple, TypeVar, Union

import numpy as np
from pydantic import BaseModel, ConfigDict, Field, field_validator

__all__ = [
    "EntityCategory",
    "EntityType",
    "SensorType",
    "SensorStatus",
    "RelationshipType",
    "BeliefDistributionType",
    "Disposition",
    "ThreatLevel",
    "AnomalySeverity",
    "ChangeType",
    "HypothesisStatus",
    "PredictionHorizon",
    "utc_now",
    "EntityID",
    "Vector3",
    "CovarianceMatrix",
    "BeliefDistribution",
    "EntityState",
    "TrackedEntity",
    "Observation",
    "SensorMeasurement",
    "Relationship",
    "PredictedState",
    "EventForecast",
    "AnomalyReport",
    "ChangeReport",
    "WorldSnapshot",
    "EvidenceLink",
    "EvidenceChain",
    "ScenarioBranch",
    "BeliefUpdate",
    "EntityFilter",
]


def utc_now() -> datetime:
    """Return the current UTC timestamp as a timezone-aware datetime."""
    return datetime.now(timezone.utc)


T = TypeVar("T")


class EntityCategory(str, Enum):
    """High-level semantic category for a simulated entity.

    Matches the platform requirement to represent friends, neutrals, unknowns,
    and environmental / infrastructural elements as generic simulation entities.
    """

    FRIEND = "friend"
    NEUTRAL = "neutral"
    UNKNOWN = "unknown"
    ENVIRONMENT = "environment"
    INFRASTRUCTURE = "infrastructure"
    WEATHER = "weather"
    TERRAIN = "terrain"
    RESOURCE = "resource"
    COMMUNICATION = "communication"


class EntityType(str, Enum):
    """Generic simulation entity type used by the world model.

    Kept intentionally generic so the platform can be used for robotics,
    simulation, and autonomous-agent research without military coupling.
    """

    VEHICLE = "vehicle"
    AIRCRAFT = "aircraft"
    VESSEL = "vessel"
    PERSON = "person"
    ANIMAL = "animal"
    BUILDING = "building"
    ROAD = "road"
    BRIDGE = "bridge"
    RIVER = "river"
    LAKE = "lake"
    FOREST = "forest"
    OPEN_TERRAIN = "open_terrain"
    OBSTACLE = "obstacle"
    WEATHER_SYSTEM = "weather_system"
    DEPOT = "depot"
    COMMUNICATION_NODE = "communication_node"
    POWER_GRID = "power_grid"
    RESOURCE_NODE = "resource_node"
    SIGNAL_EMITTER = "signal_emitter"
    UNKNOWN_TYPE = "unknown_type"


class SensorType(str, Enum):
    """Supported sensor modalities."""

    CAMERA = "camera"
    RADAR = "radar"
    LIDAR = "lidar"
    THERMAL = "thermal"
    INFRARED = "infrared"
    ACOUSTIC = "acoustic"
    RF = "rf"
    GPS = "gps"
    IMU = "imu"
    SYNTHETIC = "synthetic"
    SIMULATION = "simulation"


class SensorStatus(str, Enum):
    """Operational status of a sensor."""

    ONLINE = "online"
    DEGRADED = "degraded"
    OFFLINE = "offline"
    CALIBRATING = "calibrating"
    OBSCURED = "obscured"
    MISSING = "missing"


class RelationshipType(str, Enum):
    """Typology of relationships that can be represented in the scene graph."""

    SPATIAL_NEAR = "spatial_near"
    FOLLOWS = "follows"
    LEADS = "leads"
    CONTAINS = "contains"
    PART_OF = "part_of"
    ATTACHED_TO = "attached_to"
    INTERSECTS = "intersects"
    OCCUPIES = "occupies"
    SUPPLIES = "supplies"
    COMMUNICATES_WITH = "communicates_with"
    DEPENDS_ON = "depends_on"
    CAUSES = "causes"
    INFLUENCES = "influences"
    OPPOSES = "opposes"
    UNKNOWN_RELATION = "unknown_relation"


class BeliefDistributionType(str, Enum):
    """Parametric family of a belief distribution."""

    GAUSSIAN = "gaussian"
    PARTICLE = "particle"
    CATEGORICAL = "categorical"
    DIRICHLET = "dirichlet"
    BETA = "beta"
    MIXTURE = "mixture"
    DETERMINISTIC = "deterministic"


class Disposition(str, Enum):
    """Behavioral disposition assigned to an entity."""

    COOPERATIVE = "cooperative"
    NEUTRAL = "neutral"
    ADVERSARIAL = "adversarial"
    UNKNOWN = "unknown"
    UNRESPONSIVE = "unresponsive"


class ThreatLevel(str, Enum):
    """Ordinal threat level."""

    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AnomalySeverity(str, Enum):
    """Severity of an anomaly report."""

    INFO = "info"
    MINOR = "minor"
    MODERATE = "moderate"
    SEVERE = "severe"
    CRITICAL = "critical"


class ChangeType(str, Enum):
    """Types of change detected in the world model."""

    APPEARED = "appeared"
    DISAPPEARED = "disappeared"
    MOVED = "moved"
    ATTRIBUTE_CHANGED = "attribute_changed"
    STATE_CHANGED = "state_changed"
    RELATIONSHIP_CHANGED = "relationship_changed"
    CLASSIFICATION_CHANGED = "classification_changed"


class HypothesisStatus(str, Enum):
    """Lifecycle status of a hypothesis."""

    PROPOSED = "proposed"
    ACTIVE = "active"
    SUPPORTED = "supported"
    WEAKENED = "weakened"
    ELIMINATED = "eliminated"
    ACCEPTED = "accepted"


class PredictionHorizon(str, Enum):
    """Categorical prediction horizon."""

    IMMEDIATE = "immediate"      # < 1 s
    SHORT_TERM = "short_term"    # 1 s - 30 s
    MEDIUM_TERM = "medium_term"  # 30 s - 5 min
    LONG_TERM = "long_term"      # > 5 min


class EntityID(BaseModel):
    """Typed entity identifier backed by a UUID."""

    model_config = ConfigDict(frozen=True)

    value: uuid.UUID = Field(default_factory=uuid.uuid4)

    def __str__(self) -> str:
        return str(self.value)

    def __hash__(self) -> int:
        return hash(self.value)

    @classmethod
    def new(cls) -> "EntityID":
        return cls(value=uuid.uuid4())


class Vector3(BaseModel):
    """Three dimensional vector with numpy-backed arithmetic helpers."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    x: float = 0.0
    y: float = 0.0
    z: float = 0.0

    def as_array(self) -> np.ndarray:
        return np.array([self.x, self.y, self.z], dtype=np.float64)

    @classmethod
    def from_array(cls, arr: Sequence[float]) -> "Vector3":
        a = np.asarray(arr, dtype=np.float64)
        if a.size == 2:
            return cls(x=float(a[0]), y=float(a[1]), z=0.0)
        return cls(x=float(a[0]), y=float(a[1]), z=float(a[2]))

    def distance_to(self, other: "Vector3") -> float:
        return float(np.linalg.norm(self.as_array() - other.as_array()))

    def __add__(self, other: "Vector3") -> "Vector3":
        return Vector3.from_array(self.as_array() + other.as_array())

    def __sub__(self, other: "Vector3") -> "Vector3":
        return Vector3.from_array(self.as_array() - other.as_array())


class CovarianceMatrix(BaseModel):
    """N x N covariance matrix stored as a flat list of rows."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    dim: int = Field(ge=1)
    data: List[List[float]] = Field(default_factory=list)

    def to_array(self) -> np.ndarray:
        if not self.data:
            return np.eye(self.dim, dtype=np.float64)
        arr = np.asarray(self.data, dtype=np.float64)
        if arr.shape != (self.dim, self.dim):
            raise ValueError(
                f"Covariance shape {arr.shape} does not match dim {self.dim}"
            )
        return arr

    @classmethod
    def from_array(cls, arr: np.ndarray) -> "CovarianceMatrix":
        a = np.asarray(arr, dtype=np.float64)
        if a.ndim == 0:
            a = np.array([[float(a)]])
        if a.ndim == 1:
            a = np.diag(a)
        return cls(dim=int(a.shape[0]), data=a.tolist())

    @classmethod
    def eye(cls, dim: int, scale: float = 1.0) -> "CovarianceMatrix":
        return cls.from_array(np.eye(dim, dtype=np.float64) * scale)


class BeliefDistribution(BaseModel):
    """A probability distribution over an entity state.

    Supports Gaussian (mean + covariance), particle sets, categorical
    distributions, and deterministic point estimates. The ``data`` field holds
    modality-specific payloads (e.g., particle weights / samples).
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    distribution_type: BeliefDistributionType = BeliefDistributionType.GAUSSIAN
    mean: Optional[List[float]] = Field(default=None, description="Gaussian mean vector.")
    covariance: Optional[CovarianceMatrix] = Field(default=None, description="Gaussian covariance.")
    particles: Optional[List[List[float]]] = Field(default=None, description="Particle samples.")
    particle_weights: Optional[List[float]] = Field(default=None, description="Particle weights.")
    categorical_probs: Optional[Dict[str, float]] = Field(default=None, description="Categorical probabilities keyed by outcome label.")
    sample_count: int = Field(default=0, ge=0)

    @field_validator("categorical_probs")
    @classmethod
    def _validate_categorical(
        cls, v: Optional[Dict[str, float]]
    ) -> Optional[Dict[str, float]]:
        if v is not None:
            total = sum(v.values())
            if abs(total - 1.0) > 1e-6:
                raise ValueError(f"Categorical probabilities must sum to 1.0, got {total}")
        return v

    @classmethod
    def deterministic(cls, mean: Sequence[float]) -> "BeliefDistribution":
        m = list(mean)
        return cls(
            distribution_type=BeliefDistributionType.DETERMINISTIC,
            mean=m,
            covariance=CovarianceMatrix.eye(len(m), scale=1e-12),
            sample_count=1,
        )

    @classmethod
    def gaussian(cls, mean: Sequence[float], cov: np.ndarray) -> "BeliefDistribution":
        m = list(mean)
        return cls(
            distribution_type=BeliefDistributionType.GAUSSIAN,
            mean=m,
            covariance=CovarianceMatrix.from_array(cov),
            sample_count=1,
        )

    def mean_array(self) -> np.ndarray:
        if self.mean is not None:
            return np.asarray(self.mean, dtype=np.float64)
        if self.particles is not None:
            pts = np.asarray(self.particles, dtype=np.float64)
            w = np.asarray(self.particle_weights or [1.0 / len(pts)] * len(pts))
            return np.average(pts, axis=0, weights=w)
        if self.categorical_probs:
            # Return the most probable outcome encoded as a one-hot float list.
            outcome = max(self.categorical_probs, key=self.categorical_probs.get)
            return np.asarray(self.categorical_probs[outcome], dtype=np.float64)
        return np.zeros(0, dtype=np.float64)

    def covariance_array(self) -> np.ndarray:
        if self.covariance is not None:
            return self.covariance.to_array()
        if self.particles is not None:
            pts = np.asarray(self.particles, dtype=np.float64)
            w = np.asarray(self.particle_weights or [1.0 / len(pts)] * len(pts))
            mean = np.average(pts, axis=0, weights=w)
            diff = pts - mean
            cov = (diff * w[:, None]).T @ diff
            if cov.ndim == 0:
                cov = np.array([[float(cov)]])
            return cov
        return np.eye(max(len(self.mean or []), 1), dtype=np.float64) * 1e-12

    def uncertainty(self) -> float:
        """Scalar uncertainty metric: trace of covariance (Gaussian) or entropy."""
        if self.distribution_type in (
            BeliefDistributionType.GAUSSIAN,
            BeliefDistributionType.DETERMINISTIC,
        ):
            return float(np.trace(self.covariance_array()))
        if self.distribution_type == BeliefDistributionType.CATEGORICAL and self.categorical_probs:
            probs = np.asarray(list(self.categorical_probs.values()), dtype=np.float64)
            probs = probs[probs > 0]
            return float(-np.sum(probs * np.log(probs)))
        if self.particles is not None:
            pts = np.asarray(self.particles, dtype=np.float64)
            return float(np.trace(np.cov(pts, rowvar=False, ddof=0)))
        return float("inf")

    def entropy(self) -> float:
        """Shannon entropy of the distribution (nats)."""
        if self.distribution_type == BeliefDistributionType.CATEGORICAL and self.categorical_probs:
            probs = np.asarray(list(self.categorical_probs.values()), dtype=np.float64)
            probs = probs[probs > 0]
            return float(-np.sum(probs * np.log(probs)))
        cov = self.covariance_array()
        n = cov.shape[0]
        sign, logdet = np.linalg.slogdet(cov)
        if sign <= 0:
            return float("inf")
        return float(0.5 * (n * (1.0 + np.log(2.0 * np.pi)) + logdet))


class EntityState(BaseModel):
    """Full kinematic + attribute state of a tracked entity."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    position: Vector3 = Field(default_factory=Vector3)
    velocity: Vector3 = Field(default_factory=Vector3)
    acceleration: Vector3 = Field(default_factory=Vector3)
    orientation: Vector3 = Field(default_factory=Vector3)
    timestamp: datetime = Field(default_factory=utc_now)
    attributes: Dict[str, Any] = Field(default_factory=dict)

    def state_vector(self) -> np.ndarray:
        """9-dimensional kinematic state vector [x, y, z, vx, vy, vz, ax, ay, az]."""
        return np.concatenate(
            [
                self.position.as_array(),
                self.velocity.as_array(),
                self.acceleration.as_array(),
            ]
        )

    @classmethod
    def from_state_vector(cls, vec: Sequence[float]) -> "EntityState":
        v = np.asarray(vec, dtype=np.float64)
        if v.size < 6:
            raise ValueError("State vector must have at least 6 elements (position + velocity)")
        return cls(
            position=Vector3.from_array(v[0:3]),
            velocity=Vector3.from_array(v[3:6]),
            acceleration=Vector3.from_array(v[6:9]) if v.size >= 9 else Vector3(),
        )


class TrackedEntity(BaseModel):
    """A persistent entity maintained by the world model.

    Contains the UUID, current belief, uncertainty, confidence, history,
    associated observations, inferred properties, relationships and projected
    futures -- satisfying the world-model requirement for a rich entity record.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    entity_id: EntityID = Field(default_factory=EntityID.new)
    entity_type: EntityType = EntityType.UNKNOWN_TYPE
    category: EntityCategory = EntityCategory.UNKNOWN
    disposition: Disposition = Disposition.UNKNOWN
    state: EntityState = Field(default_factory=EntityState)
    belief: BeliefDistribution = Field(default_factory=lambda: BeliefDistribution.deterministic([0.0, 0.0, 0.0]))
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    uncertainty: float = Field(default=float("inf"))
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)
    last_observed_at: Optional[datetime] = None
    observation_count: int = Field(default=0, ge=0)
    observation_ids: List[str] = Field(default_factory=list)
    inferred_properties: Dict[str, Any] = Field(default_factory=dict)
    relationship_ids: List[str] = Field(default_factory=list)
    predicted_states: List["PredictedState"] = Field(default_factory=list)
    history: List[EntityState] = Field(default_factory=list)
    labels: Dict[str, str] = Field(default_factory=dict)

    @field_validator("confidence")
    @classmethod
    def _clamp_confidence(cls, v: float) -> float:
        return float(max(0.0, min(1.0, v)))


class Observation(BaseModel):
    """A validated observation of an entity from a sensor."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    observation_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    sensor_id: str
    timestamp: datetime = Field(default_factory=utc_now)
    measurement: SensorMeasurement
    entity_id: Optional[EntityID] = None
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    is_noisy: bool = False
    is_missing: bool = False
    validated: bool = True
    validation_reason: str = ""
    metadata: Dict[str, Any] = Field(default_factory=dict)


class SensorMeasurement(BaseModel):
    """Raw or preprocessed measurement payload produced by a sensor."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    value: Any
    covariance: Optional[CovarianceMatrix] = None
    signal_to_noise: Optional[float] = None
    modality: Optional[SensorType] = None
    units: str = ""
    detection_class: Optional[str] = None
    segmentation_mask: Optional[Any] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class Relationship(BaseModel):
    """A typed edge between two entities in the scene/knowledge graph."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    relationship_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    source_id: EntityID
    target_id: EntityID
    relationship_type: RelationshipType
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    attributes: Dict[str, Any] = Field(default_factory=dict)
    first_seen: datetime = Field(default_factory=utc_now)
    last_updated: datetime = Field(default_factory=utc_now)
    evidence: List[str] = Field(default_factory=list)


class PredictedState(BaseModel):
    """A projection of an entity's future state at a given horizon."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    entity_id: EntityID
    horizon_seconds: float = Field(gt=0.0)
    predicted_at: datetime = Field(default_factory=utc_now)
    state: EntityState = Field(default_factory=EntityState)
    belief: BeliefDistribution = Field(default_factory=lambda: BeliefDistribution.deterministic([0.0, 0.0, 0.0]))
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    method: str = "unknown"
    scenario: str = "nominal"
    metadata: Dict[str, Any] = Field(default_factory=dict)


class EventForecast(BaseModel):
    """Forecast of a future event with a probability."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    event_type: str
    probability: float = Field(ge=0.0, le=1.0)
    time_to_event: Optional[float] = Field(default=None, ge=0.0, description="Expected seconds until event.")
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    affected_entity_ids: List[EntityID] = Field(default_factory=list)
    contributing_factors: List[str] = Field(default_factory=list)
    generated_at: datetime = Field(default_factory=utc_now)
    method: str = "unknown"
    metadata: Dict[str, Any] = Field(default_factory=dict)


class AnomalyReport(BaseModel):
    """A detected deviation from expected behavior or state."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    anomaly_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    entity_id: Optional[EntityID] = None
    sensor_id: Optional[str] = None
    description: str
    severity: AnomalySeverity = AnomalySeverity.INFO
    score: float = Field(default=0.0, ge=0.0, le=1.0)
    expected: Optional[Any] = None
    observed: Optional[Any] = None
    detected_at: datetime = Field(default_factory=utc_now)
    related_observation_ids: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ChangeReport(BaseModel):
    """A detected change in the world model."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    change_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    change_type: ChangeType
    entity_id: Optional[EntityID] = None
    attribute: Optional[str] = None
    previous_value: Optional[Any] = None
    new_value: Optional[Any] = None
    significance: float = Field(default=0.0, ge=0.0, le=1.0)
    detected_at: datetime = Field(default_factory=utc_now)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class WorldSnapshot(BaseModel):
    """Immutable snapshot of the world model at a point in time."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    captured_at: datetime = Field(default_factory=utc_now)
    entities: List[TrackedEntity] = Field(default_factory=list)
    relationships: List[Relationship] = Field(default_factory=list)
    observations: List[Observation] = Field(default_factory=list)
    sequence: int = Field(default=0, ge=0)


class EvidenceLink(BaseModel):
    """A single contribution to an explanatory evidence chain."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    source: str
    description: str
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    timestamp: datetime = Field(default_factory=utc_now)
    observation_id: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class EvidenceChain(BaseModel):
    """An ordered chain of evidence supporting a belief update or conclusion."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    conclusion: str
    links: List[EvidenceLink] = Field(default_factory=list)
    overall_confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    reasoning_graph: Dict[str, Any] = Field(default_factory=dict)
    alternative_hypotheses: List[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=utc_now)


class ScenarioBranch(BaseModel):
    """A branching scenario projection for Monte-Carlo style analysis."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    branch_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    scenario: str = "nominal"
    probability: float = Field(default=0.0, ge=0.0, le=1.0)
    predicted_states: List[PredictedState] = Field(default_factory=list)
    events: List[EventForecast] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class BeliefUpdate(BaseModel):
    """A record of how a belief was revised."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    entity_id: EntityID
    timestamp: datetime = Field(default_factory=utc_now)
    previous_belief: Optional[BeliefDistribution] = None
    updated_belief: Optional[BeliefDistribution] = None
    information_gain: float = Field(default=0.0, ge=0.0)
    confidence_delta: float = Field(default=0.0)
    contributing_observation_ids: List[str] = Field(default_factory=list)
    method: str = "unknown"
    metadata: Dict[str, Any] = Field(default_factory=dict)


class EntityFilter(BaseModel):
    """Criteria for selecting entities from the world model."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    categories: Optional[List[EntityCategory]] = None
    entity_types: Optional[List[EntityType]] = None
    dispositions: Optional[List[Disposition]] = None
    min_confidence: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    max_uncertainty: Optional[float] = Field(default=None, ge=0.0)
    within_radius_of: Optional[Vector3] = None
    radius: Optional[float] = Field(default=None, ge=0.0)
    updated_after: Optional[datetime] = None