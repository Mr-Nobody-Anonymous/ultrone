# Copyright (c) Ultrone Contributors. All rights reserved.
"""Awareness engine orchestrator.

Implements the three Endsley levels of situational awareness:

* **Level 1 (Perception)** -- multi-sensor ingestion, validation, fusion
* **Level 2 (Comprehension)** -- world model, scene graph, semantic map,
  threat assessment, anomaly detection, intent estimation
* **Level 3 (Projection)** -- trajectory prediction, event prediction,
  uncertainty propagation

The engine wires together all subsystems via dependency injection and
provides a single async entry point for the full awareness pipeline.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, List, Optional, Sequence

import numpy as np

from .active_perception import ActivePerception
from .anomaly_detector import AnomalyDetector
from .attention_manager import AttentionManager
from .belief_state import BeliefStateEstimator
from .causal_reasoner import CausalReasoner
from .change_detector import ChangeDetector
from .confidence_engine import ConfidenceEngine
from .context_engine import ContextEngine
from .dynamic_map import DynamicMap
from .entity_tracker import EntityTracker
from .event_predictor import EventPredictor
from .events import EventBus, ObservationReceived
from .explainability import ExplainabilityEngine
from .hypothesis_manager import HypothesisManager
from .information_gain import InformationGainEstimator
from .intent_estimator import IntentEstimator
from .object_memory import ObjectMemory
from .observation_history import ObservationHistory
from .observation_validation import ObservationValidator
from .scene_graph import SceneGraph
from .semantic_mapper import SemanticMap
from .sensor_fusion import SensorFusionEngine
from .sensor_registry import SensorRegistry
from .telemetry import PerformanceTelemetry
from .temporal_reasoner import TemporalReasoner
from .threat_assessor import ThreatAssessor
from .trajectory_predictor import TrajectoryPredictor
from .types import (
    CovarianceMatrix,
    EntityCategory,
    EntityID,
    EntityType,
    Observation,
    RelationshipType,
    SensorMeasurement,
    TrackedEntity,
    Vector3,
    WorldSnapshot,
    utc_now,
)
from .uncertainty_engine import UncertaintyEngine
from .uncertainty_propagation import UncertaintyPropagator
from .visualization import VisualizationEngine
from .world_model import WorldModel
from .world_state_cache import WorldStateCache

__all__ = [
    "AwarenessEngine",
    "AwarenessEngineConfig",
    "AwarenessReport",
]


@dataclass
class AwarenessReport:
    """A comprehensive report of the awareness state."""

    snapshot: WorldSnapshot
    threat_assessments: List[Any] = field(default_factory=list)
    anomaly_reports: List[Any] = field(default_factory=list)
    change_reports: List[Any] = field(default_factory=list)
    intent_estimates: List[Any] = field(default_factory=list)
    event_forecasts: List[Any] = field(default_factory=list)
    trajectory_predictions: List[Any] = field(default_factory=list)
    generated_at: datetime = field(default_factory=utc_now)


class AwarenessEngineConfig:
    """Configuration for the awareness engine."""

    def __init__(
        self,
        *,
        fusion_strategy: str = "bayesian",
        track_history: bool = True,
        enable_anomaly_detection: bool = True,
        enable_threat_assessment: bool = True,
        enable_intent_estimation: bool = True,
        enable_prediction: bool = True,
        enable_explainability: bool = True,
    ) -> None:
        self.fusion_strategy = fusion_strategy
        self.track_history = track_history
        self.enable_anomaly_detection = enable_anomaly_detection
        self.enable_threat_assessment = enable_threat_assessment
        self.enable_intent_estimation = enable_intent_estimation
        self.enable_prediction = enable_prediction
        self.enable_explainability = enable_explainability


class AwarenessEngine:
    """Orchestrates the full situational awareness pipeline."""

    def __init__(
        self,
        *,
        config: Optional[AwarenessEngineConfig] = None,
        event_bus: Optional[EventBus] = None,
        telemetry: Optional[PerformanceTelemetry] = None,
    ) -> None:
        self._config = config or AwarenessEngineConfig()
        self._event_bus = event_bus or EventBus()
        self._telemetry = telemetry or PerformanceTelemetry()

        # Core infrastructure.
        self.world_model = WorldModel(
            event_bus=self._event_bus,
            telemetry=self._telemetry,
        )
        self.sensor_registry = SensorRegistry()
        self.sensor_fusion = SensorFusionEngine(
            default_strategy=self._config.fusion_strategy
        )
        self.belief_estimator = BeliefStateEstimator()
        self.observation_validator = ObservationValidator()
        self.entity_tracker = EntityTracker()
        self.observation_history = ObservationHistory()

        # Level 2: Comprehension.
        self.scene_graph = SceneGraph()
        self.semantic_map = SemanticMap()
        self.dynamic_map = DynamicMap()
        self.temporal_reasoner = TemporalReasoner()
        self.causal_reasoner = CausalReasoner()
        self.threat_assessor = ThreatAssessor()
        self.anomaly_detector = AnomalyDetector(event_bus=self._event_bus)
        self.intent_estimator = IntentEstimator()
        self.context_engine = ContextEngine()
        self.confidence_engine = ConfidenceEngine()
        self.uncertainty_engine = UncertaintyEngine()
        self.uncertainty_propagator = UncertaintyPropagator()
        self.change_detector = ChangeDetector(event_bus=self._event_bus)
        self.hypothesis_manager = HypothesisManager(event_bus=self._event_bus)
        self.object_memory = ObjectMemory()

        # Level 3: Projection.
        self.trajectory_predictor = TrajectoryPredictor()
        self.event_predictor = EventPredictor()

        # Attention and active perception.
        self.attention_manager = AttentionManager(event_bus=self._event_bus)
        self.information_gain_estimator = InformationGainEstimator()
        self.active_perception = ActivePerception(
            information_gain_estimator=self.information_gain_estimator
        )

        # Explainability and visualization.
        self.explainability = ExplainabilityEngine()
        self.visualization = VisualizationEngine()

        # Cache.
        self.world_state_cache = WorldStateCache()

        # Wire the entity tracker to the world model's entity store.
        self.entity_tracker.set_entities(self.world_model._entities)

    # ------------------------------------------------------------------
    # Level 1: Perception
    # ------------------------------------------------------------------

    async def ingest_observation(
        self,
        *,
        sensor_id: str,
        value: Any,
        entity_id: Optional[EntityID] = None,
        confidence: float = 0.5,
        covariance: Optional[np.ndarray] = None,
        detection_class: Optional[str] = None,
        is_noisy: bool = False,
        is_missing: bool = False,
    ) -> Optional[Observation]:
        """Ingest a raw sensor observation through the perception pipeline."""
        measurement = SensorMeasurement(
            value=value,
            covariance=None if covariance is None else CovarianceMatrix.from_array(covariance),
            detection_class=detection_class,
        )
        observation = Observation(
            sensor_id=sensor_id,
            measurement=measurement,
            entity_id=entity_id,
            confidence=confidence,
            is_noisy=is_noisy,
            is_missing=is_missing,
        )

        # Validate.
        validation = self.observation_validator.validate(observation)
        if not validation.valid:
            return None
        observation = validation.corrected or observation

        # Record in history.
        self.observation_history.add(observation)

        # Associate with an entity.
        if observation.entity_id is None:
            association = self.entity_tracker.associate(observation)
            if association.associated:
                observation.entity_id = association.entity_id

        # Emit event.
        await self._event_bus.publish(
            ObservationReceived(
                observation_id=observation.observation_id,
                sensor_id=observation.sensor_id,
                entity_id=str(observation.entity_id) if observation.entity_id else None,
                confidence=observation.confidence,
            )
        )
        return observation

    async def ingest_batch(
        self, observations: Sequence[Observation]
    ) -> List[Observation]:
        """Ingest a batch of observations."""
        results: List[Observation] = []
        for obs in observations:
            result = await self.ingest_observation(
                sensor_id=obs.sensor_id,
                value=obs.measurement.value,
                entity_id=obs.entity_id,
                confidence=obs.confidence,
                detection_class=obs.measurement.detection_class,
                is_noisy=obs.is_noisy,
                is_missing=obs.is_missing,
            )
            if result is not None:
                results.append(result)
        return results

    # ------------------------------------------------------------------
    # Level 2: Comprehension
    # ------------------------------------------------------------------

    def update_entity_from_observation(
        self, observation: Observation
    ) -> Optional[TrackedEntity]:
        """Update or create an entity from a validated observation."""
        if observation.entity_id is None:
            return None

        entity = self.world_model.get_entity(observation.entity_id)
        if entity is None:
            # Create a new entity.
            value = observation.measurement.value
            if isinstance(value, (list, tuple, np.ndarray)):
                arr = np.asarray(value, dtype=np.float64)
                position = Vector3.from_array(arr[:3]) if arr.size >= 3 else Vector3()
            else:
                position = Vector3()
            entity = self.world_model.create_entity(
                entity_type=EntityType.UNKNOWN_TYPE,
                category=EntityCategory.UNKNOWN,
                position=position,
                confidence=observation.confidence,
            )
            self.entity_tracker.create_track(observation, entity)

        # Record observation.
        self.world_model.record_observation(observation)

        # Update belief.
        value = observation.measurement.value
        if isinstance(value, (list, tuple, np.ndarray)):
            arr = np.asarray(value, dtype=np.float64)
            cov = (
                observation.measurement.covariance.to_array()
                if observation.measurement.covariance
                else np.eye(arr.shape[0], dtype=np.float64) * 0.1
            )
            if self.belief_estimator.get_belief(entity.entity_id) is None:
                self.belief_estimator.initialize_gaussian(
                    entity.entity_id, arr, cov
                )
            else:
                self.belief_estimator.gaussian_update(
                    entity.entity_id,
                    arr,
                    cov,
                    observation_id=observation.observation_id,
                )
            belief = self.belief_estimator.get_belief(entity.entity_id)
            if belief is not None:
                uncertainty = belief.uncertainty()
                self.world_model.update_entity(
                    entity.entity_id,
                    belief=belief,
                    uncertainty=uncertainty,
                    confidence=observation.confidence,
                )

        # Update scene graph and dynamic map.
        self.scene_graph.add_entity(entity)
        self.dynamic_map.update_entity(entity)

        # Update object memory.
        self.object_memory.observe(entity, observation)

        return entity

    def update_relationships(self) -> None:
        """Update spatial relationships between nearby entities."""
        entities = self.world_model.query()
        for i, entity_a in enumerate(entities):
            for entity_b in entities[i + 1 :]:
                distance = entity_a.state.position.distance_to(entity_b.state.position)
                if distance < 10.0:
                    self.world_model.add_relationship(
                        entity_a.entity_id,
                        entity_b.entity_id,
                        RelationshipType.SPATIAL_NEAR,
                        confidence=max(0.0, 1.0 - distance / 10.0),
                    )

    def assess_entities(self) -> None:
        """Run comprehension assessments on all entities."""
        entities = self.world_model.query()

        # Threat assessment.
        if self._config.enable_threat_assessment:
            for entity in entities:
                assessment = self.threat_assessor.assess(entity)
                entity.inferred_properties["threat_score"] = assessment.threat_score
                entity.inferred_properties["threat_level"] = assessment.threat_level.value

        # Anomaly detection.
        if self._config.enable_anomaly_detection:
            for entity in entities:
                self.anomaly_detector.analyze_entity(entity)

        # Intent estimation.
        if self._config.enable_intent_estimation:
            for entity in entities:
                estimate = self.intent_estimator.estimate(entity)
                entity.inferred_properties["intent"] = estimate.intent
                entity.inferred_properties["intent_probability"] = estimate.probability

        # Temporal analysis.
        for entity in entities:
            self.temporal_reasoner.analyze_entity(entity)

        # Change detection.
        for entity in entities:
            self.change_detector.detect(entity)
        self.change_detector.detect_disappearance(
            [e.entity_id for e in entities]
        )

        # Update relationships.
        self.update_relationships()

    # ------------------------------------------------------------------
    # Level 3: Projection
    # ------------------------------------------------------------------

    def project(self, horizon_seconds: float = 30.0) -> None:
        """Run projection (Level 3) on all entities."""
        if not self._config.enable_prediction:
            return
        entities = self.world_model.query()
        for entity in entities:
            # Trajectory prediction.
            prediction = self.trajectory_predictor.predict(
                entity, horizons=[horizon_seconds]
            )
            predicted_states = self.trajectory_predictor.to_predicted_states(prediction)
            self.world_model.store_predictions(entity.entity_id, predicted_states)

            # Event prediction.
            self.event_predictor.predict_entity(
                entity, horizon_seconds=horizon_seconds
            )

            # Uncertainty propagation.
            self.uncertainty_propagator.propagate(
                entity, horizon_seconds=horizon_seconds
            )

    # ------------------------------------------------------------------
    # Full pipeline
    # ------------------------------------------------------------------

    async def tick(
        self,
        *,
        horizon_seconds: float = 30.0,
        commit: bool = True,
    ) -> AwarenessReport:
        """Run one full awareness cycle (perceive, comprehend, project)."""
        # Level 2: Comprehension.
        self.assess_entities()

        # Level 3: Projection.
        self.project(horizon_seconds=horizon_seconds)

        # Commit the world state.
        snapshot = self.world_model.commit_tick() if commit else self.world_model.snapshot()

        # Cache.
        self.world_state_cache.put_snapshot(snapshot)

        # Build report.
        report = AwarenessReport(
            snapshot=snapshot,
            threat_assessments=[
                e.inferred_properties.get("threat_score", 0.0)
                for e in snapshot.entities
            ],
            anomaly_reports=self.anomaly_detector.reports(),
            change_reports=self.change_detector.reports(),
            intent_estimates=self.intent_estimator.estimates(),
            event_forecasts=self.event_predictor.forecasts(),
            trajectory_predictions=self.trajectory_predictor.predictions(),
        )
        return report

    def get_snapshot(self) -> WorldSnapshot:
        """Get the current world snapshot."""
        return self.world_model.snapshot()

    def get_entity(self, entity_id: EntityID) -> Optional[TrackedEntity]:
        return self.world_model.get_entity(entity_id)

    def query_entities(self) -> List[TrackedEntity]:
        return self.world_model.query()

    def summary(self) -> str:
        """Generate a human-readable situational summary."""
        return self.visualization.situational_summary(self.get_snapshot())

    async def close(self) -> None:
        """Release resources."""
        await self._event_bus.close()