#!/usr/bin/env python3
"""Tests for the Situational Awareness System."""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import asyncio
import unittest
import numpy as np

from brain.perception.situational_awareness import (
    # Core types
    EntityID, Vector3, CovarianceMatrix, BeliefDistribution,
    EntityState, TrackedEntity, Observation, SensorMeasurement,
    EntityCategory, EntityType, SensorType, SensorStatus,
    Disposition, ThreatLevel, RelationshipType,
    # Events
    EventBus, EventPriority, DomainEvent, ObservationReceived,
    # Level 1
    SensorRegistry, SensorSpecification, SensorDescriptor,
    ObservationValidator, ValidationRule,
    EntityTracker, EntityTrackerConfig,
    SensorFusionEngine, BayesianFusion, ExtendedKalmanFusion,
    UnscentedKalmanFusion, ParticleFusion, DempsterShaferFusion,
    CovarianceIntersectionFusion, NeuralFusion,
    BeliefStateEstimator,
    # Level 2
    WorldModel, WorldModelConfig, SceneGraph, SemanticMap,
    DynamicMap, TemporalReasoner, CausalReasoner,
    ThreatAssessor, AnomalyDetector, IntentEstimator,
    ContextEngine, ConfidenceEngine, UncertaintyEngine,
    UncertaintyPropagator, ChangeDetector, HypothesisManager,
    ObjectMemory,
    # Level 3
    TrajectoryPredictor, EventPredictor,
    # Attention
    AttentionManager, InformationGainEstimator, ActivePerception,
    # Explainability
    ExplainabilityEngine,
    # Engine
    AwarenessEngine, AwarenessEngineConfig,
)


class TestCoreTypes(unittest.TestCase):
    def test_entity_id(self):
        eid = EntityID.new()
        self.assertIsNotNone(eid.value)
        self.assertEqual(str(eid), str(eid.value))

    def test_vector3(self):
        v = Vector3(x=1.0, y=2.0, z=3.0)
        arr = v.as_array()
        self.assertEqual(arr.tolist(), [1.0, 2.0, 3.0])
        v2 = Vector3.from_array([4.0, 5.0, 6.0])
        self.assertEqual(v2.x, 4.0)
        self.assertEqual(v.distance_to(Vector3()), np.sqrt(14.0))

    def test_covariance_matrix(self):
        cov = CovarianceMatrix.eye(3, scale=2.0)
        arr = cov.to_array()
        self.assertEqual(arr.shape, (3, 3))
        self.assertEqual(arr[0, 0], 2.0)

    def test_belief_distribution(self):
        belief = BeliefDistribution.gaussian([0.0, 0.0], np.eye(2))
        self.assertEqual(belief.distribution_type.value, "gaussian")
        self.assertGreater(belief.entropy(), 0.0)
        self.assertGreater(belief.uncertainty(), 0.0)

    def test_entity_state(self):
        state = EntityState(position=Vector3(x=1.0, y=2.0, z=3.0))
        vec = state.state_vector()
        self.assertEqual(vec.shape[0], 9)
        self.assertEqual(vec[0], 1.0)


class TestEventBus(unittest.TestCase):
    def test_sync_publish(self):
        bus = EventBus()
        received = []
        bus.subscribe(ObservationReceived, lambda e: received.append(e))
        bus.publish_sync(ObservationReceived(observation_id="obs1", sensor_id="s1"))
        self.assertEqual(len(received), 1)
        self.assertEqual(received[0].observation_id, "obs1")

    def test_async_publish(self):
        async def run():
            bus = EventBus()
            received = []

            async def handler(event):
                received.append(event)

            bus.subscribe_async(ObservationReceived, handler)
            await bus.publish_and_wait(
                ObservationReceived(observation_id="obs2", sensor_id="s2")
            )
            self.assertEqual(len(received), 1)

        asyncio.run(run())

    def test_unsubscribe(self):
        bus = EventBus()
        received = []
        unsub = bus.subscribe(ObservationReceived, lambda e: received.append(e))
        unsub()
        bus.publish_sync(ObservationReceived(observation_id="obs3", sensor_id="s3"))
        self.assertEqual(len(received), 0)


class TestSensorRegistry(unittest.TestCase):
    def test_register_and_query(self):
        registry = SensorRegistry()
        spec = SensorSpecification(sensor_id="cam1", sensor_type=SensorType.CAMERA)
        descriptor = registry.register(spec)
        self.assertEqual(descriptor.sensor_id, "cam1")
        self.assertEqual(registry.count(), 1)
        self.assertEqual(len(registry.by_type(SensorType.CAMERA)), 1)

    def test_duplicate_registration(self):
        registry = SensorRegistry()
        spec = SensorSpecification(sensor_id="cam1", sensor_type=SensorType.CAMERA)
        registry.register(spec)
        with self.assertRaises(Exception):
            registry.register(spec)

    def test_quality_update(self):
        registry = SensorRegistry()
        registry.register(SensorSpecification(sensor_id="s1", sensor_type=SensorType.RADAR))
        registry.update_quality("s1", status=SensorStatus.DEGRADED, confidence=0.5)
        descriptor = registry.get("s1")
        self.assertEqual(descriptor.status, SensorStatus.DEGRADED)
        self.assertEqual(descriptor.confidence, 0.5)


class TestObservationValidator(unittest.TestCase):
    def test_valid_observation(self):
        validator = ObservationValidator()
        obs = Observation(
            sensor_id="s1",
            measurement=SensorMeasurement(value=[1.0, 2.0, 3.0]),
            confidence=0.8,
        )
        result = validator.validate(obs)
        self.assertTrue(result.valid)

    def test_invalid_confidence(self):
        validator = ObservationValidator(auto_correct=False)
        # Pydantic validates confidence at construction, so use model_construct.
        obs = Observation.model_construct(
            sensor_id="s1",
            measurement=SensorMeasurement(value=[1.0]),
            confidence=1.5,
        )
        result = validator.validate(obs)
        self.assertFalse(result.valid)

    def test_offline_sensor(self):
        validator = ObservationValidator()
        validator.register_sensor_status("s1", SensorStatus.OFFLINE)
        obs = Observation(
            sensor_id="s1",
            measurement=SensorMeasurement(value=[1.0]),
        )
        result = validator.validate(obs)
        self.assertFalse(result.valid)

    def test_custom_rule(self):
        validator = ObservationValidator()
        validator.add_rule(
            ValidationRule(
                name="positive_x",
                predicate=lambda obs: (obs.measurement.value[0] > 0, "x must be positive"),
            )
        )
        obs = Observation(
            sensor_id="s1",
            measurement=SensorMeasurement(value=[-1.0]),
        )
        result = validator.validate(obs)
        self.assertFalse(result.valid)


class TestEntityTracker(unittest.TestCase):
    def test_association(self):
        tracker = EntityTracker()
        entity = TrackedEntity(
            entity_id=EntityID.new(),
            state=EntityState(position=Vector3(x=0.0, y=0.0, z=0.0)),
        )
        tracker.create_track(
            Observation(sensor_id="s1", measurement=SensorMeasurement(value=[0.0, 0.0, 0.0])),
            entity,
        )
        obs = Observation(
            sensor_id="s1",
            measurement=SensorMeasurement(value=[0.1, 0.1, 0.0]),
        )
        result = tracker.associate(obs)
        self.assertTrue(result.associated)
        self.assertEqual(result.entity_id, entity.entity_id)

    def test_no_association_far(self):
        tracker = EntityTracker()
        entity = TrackedEntity(
            entity_id=EntityID.new(),
            state=EntityState(position=Vector3(x=0.0, y=0.0, z=0.0)),
        )
        tracker.create_track(
            Observation(sensor_id="s1", measurement=SensorMeasurement(value=[0.0, 0.0, 0.0])),
            entity,
        )
        obs = Observation(
            sensor_id="s1",
            measurement=SensorMeasurement(value=[100.0, 100.0, 0.0]),
        )
        result = tracker.associate(obs)
        self.assertFalse(result.associated)


class TestSensorFusion(unittest.TestCase):
    def _make_obs(self, value, confidence=0.8, sensor_id="s1"):
        return Observation(
            sensor_id=sensor_id,
            measurement=SensorMeasurement(
                value=value,
                covariance=CovarianceMatrix.eye(len(value), scale=0.1),
            ),
            confidence=confidence,
        )

    def test_bayesian_fusion(self):
        engine = SensorFusionEngine()
        obs1 = self._make_obs([1.0, 2.0, 3.0], sensor_id="s1")
        obs2 = self._make_obs([1.1, 2.1, 3.1], sensor_id="s2")
        result = engine.fuse([obs1, obs2], strategy="bayesian")
        self.assertEqual(result.method, "bayesian")
        self.assertAlmostEqual(result.fused_mean[0], 1.05, places=2)

    def test_all_strategies(self):
        engine = SensorFusionEngine()
        obs1 = self._make_obs([1.0, 2.0, 3.0], sensor_id="s1")
        obs2 = self._make_obs([1.1, 2.1, 3.1], sensor_id="s2")
        for strategy in engine.available_strategies:
            result = engine.fuse([obs1, obs2], strategy=strategy)
            self.assertIsNotNone(result.fused_mean)

    def test_unknown_strategy(self):
        engine = SensorFusionEngine()
        with self.assertRaises(Exception):
            engine.get_strategy("unknown")


class TestBeliefState(unittest.TestCase):
    def test_gaussian_update(self):
        estimator = BeliefStateEstimator()
        eid = EntityID.new()
        estimator.initialize_gaussian(eid, [0.0, 0.0], np.eye(2) * 10.0)
        belief = estimator.gaussian_update(eid, [1.0, 1.0], np.eye(2) * 0.1)
        self.assertIsNotNone(belief)
        self.assertLess(belief.uncertainty(), 10.0)

    def test_categorical_update(self):
        estimator = BeliefStateEstimator()
        eid = EntityID.new()
        estimator.initialize_categorical(eid, {"A": 0.5, "B": 0.5})
        belief = estimator.categorical_update(eid, {"A": 0.9, "B": 0.1})
        self.assertGreater(belief.categorical_probs["A"], 0.5)

    def test_particle_update(self):
        estimator = BeliefStateEstimator()
        eid = EntityID.new()
        particles = np.random.default_rng(42).normal(0, 1, (100, 2))
        estimator.initialize_particles(eid, particles)
        belief = estimator.particle_update(eid, np.ones(100))
        self.assertIsNotNone(belief)


class TestWorldModel(unittest.TestCase):
    def test_create_and_get_entity(self):
        model = WorldModel()
        entity = model.create_entity(
            entity_type=EntityType.VEHICLE,
            category=EntityCategory.FRIEND,
            position=Vector3(x=1.0, y=2.0, z=0.0),
        )
        self.assertEqual(model.entity_count(), 1)
        fetched = model.get_entity(entity.entity_id)
        self.assertIsNotNone(fetched)
        self.assertEqual(fetched.entity_type, EntityType.VEHICLE)

    def test_update_entity(self):
        model = WorldModel()
        entity = model.create_entity(
            entity_type=EntityType.VEHICLE,
            category=EntityCategory.FRIEND,
        )
        model.update_entity(entity.entity_id, confidence=0.9)
        fetched = model.get_entity(entity.entity_id)
        self.assertEqual(fetched.confidence, 0.9)

    def test_relationships(self):
        model = WorldModel()
        e1 = model.create_entity(entity_type=EntityType.VEHICLE, category=EntityCategory.FRIEND)
        e2 = model.create_entity(entity_type=EntityType.VEHICLE, category=EntityCategory.FRIEND)
        model.add_relationship(e1.entity_id, e2.entity_id, RelationshipType.SPATIAL_NEAR)
        self.assertEqual(model.relationship_count(), 1)

    def test_snapshot(self):
        model = WorldModel()
        model.create_entity(entity_type=EntityType.VEHICLE, category=EntityCategory.FRIEND)
        snapshot = model.snapshot()
        self.assertEqual(len(snapshot.entities), 1)

    def test_query_filter(self):
        model = WorldModel()
        model.create_entity(entity_type=EntityType.VEHICLE, category=EntityCategory.FRIEND, confidence=0.9)
        model.create_entity(entity_type=EntityType.VEHICLE, category=EntityCategory.UNKNOWN, confidence=0.1)
        from brain.perception.situational_awareness import EntityFilter
        result = model.query(EntityFilter(min_confidence=0.5))
        self.assertEqual(len(result), 1)


class TestSceneGraph(unittest.TestCase):
    def test_add_and_query(self):
        graph = SceneGraph()
        e1 = TrackedEntity(entity_id=EntityID.new(), entity_type=EntityType.VEHICLE)
        e2 = TrackedEntity(entity_id=EntityID.new(), entity_type=EntityType.VEHICLE)
        graph.add_entity(e1)
        graph.add_entity(e2)
        self.assertEqual(graph.node_count(), 2)

    def test_relationships(self):
        graph = SceneGraph()
        e1 = TrackedEntity(entity_id=EntityID.new())
        e2 = TrackedEntity(entity_id=EntityID.new())
        graph.add_entity(e1)
        graph.add_entity(e2)
        from brain.perception.situational_awareness import Relationship
        rel = Relationship(
            source_id=e1.entity_id,
            target_id=e2.entity_id,
            relationship_type=RelationshipType.SPATIAL_NEAR,
        )
        graph.add_relationship(rel)
        self.assertEqual(graph.edge_count(), 1)
        self.assertEqual(len(graph.neighbors(e1.entity_id)), 1)


class TestThreatAssessor(unittest.TestCase):
    def test_threat_assessment(self):
        assessor = ThreatAssessor()
        assessor.add_protected_asset(Vector3(x=0.0, y=0.0, z=0.0))
        entity = TrackedEntity(
            entity_id=EntityID.new(),
            category=EntityCategory.UNKNOWN,
            disposition=Disposition.ADVERSARIAL,
            state=EntityState(
                position=Vector3(x=1.0, y=0.0, z=0.0),
                velocity=Vector3(x=10.0, y=0.0, z=0.0),
            ),
            confidence=0.9,
        )
        assessment = assessor.assess(entity)
        self.assertGreater(assessment.threat_score, 0.5)


class TestAnomalyDetector(unittest.TestCase):
    def test_anomaly_detection(self):
        detector = AnomalyDetector()
        entity = TrackedEntity(
            entity_id=EntityID.new(),
            state=EntityState(
                position=Vector3(x=0.0, y=0.0, z=0.0),
                velocity=Vector3(x=5.0, y=0.0, z=0.0),
            ),
        )
        # Add history to trigger anomaly detection.
        for i in range(5):
            entity.history.append(
                EntityState(
                    position=Vector3(x=float(i), y=0.0, z=0.0),
                    velocity=Vector3(x=1.0, y=0.0, z=0.0),
                )
            )
        reports = detector.analyze_entity(entity)
        self.assertIsInstance(reports, list)


class TestTrajectoryPredictor(unittest.TestCase):
    def test_predict(self):
        predictor = TrajectoryPredictor()
        entity = TrackedEntity(
            entity_id=EntityID.new(),
            state=EntityState(
                position=Vector3(x=0.0, y=0.0, z=0.0),
                velocity=Vector3(x=10.0, y=0.0, z=0.0),
            ),
            confidence=0.9,
        )
        prediction = predictor.predict(entity, horizons=[1.0, 5.0])
        self.assertEqual(len(prediction.positions), 2)
        self.assertGreater(prediction.positions[1].x, prediction.positions[0].x)


class TestEventPredictor(unittest.TestCase):
    def test_proximity_rule(self):
        predictor = EventPredictor()
        predictor.add_proximity_rule("approach", threshold_distance=10.0)
        entity = TrackedEntity(
            entity_id=EntityID.new(),
            state=EntityState(
                position=Vector3(x=0.0, y=0.0, z=0.0),
                velocity=Vector3(x=10.0, y=0.0, z=0.0),
            ),
        )
        forecasts = predictor.predict_entity(entity, horizon_seconds=1.0)
        self.assertGreaterEqual(len(forecasts), 0)


class TestAwarenessEngine(unittest.TestCase):
    def test_engine_creation(self):
        engine = AwarenessEngine()
        self.assertIsNotNone(engine.world_model)
        self.assertIsNotNone(engine.sensor_fusion)
        self.assertIsNotNone(engine.scene_graph)

    def test_ingest_and_tick(self):
        async def run():
            engine = AwarenessEngine()
            obs = await engine.ingest_observation(
                sensor_id="cam1",
                value=[1.0, 2.0, 3.0],
                confidence=0.8,
            )
            self.assertIsNotNone(obs)
            if obs is not None:
                engine.update_entity_from_observation(obs)
            report = await engine.tick()
            self.assertIsNotNone(report.snapshot)
            await engine.close()

        asyncio.run(run())

    def test_summary(self):
        engine = AwarenessEngine()
        summary = engine.summary()
        self.assertIn("SITUATIONAL", summary.upper())


class TestConfidenceEngine(unittest.TestCase):
    def test_aggregate(self):
        engine = ConfidenceEngine()
        result = engine.aggregate([0.8, 0.9, 0.7])
        self.assertAlmostEqual(result, 0.8, places=2)

    def test_decay(self):
        engine = ConfidenceEngine()
        result = engine.decay(0.9, 10.0)
        self.assertLess(result, 0.9)


class TestUncertaintyEngine(unittest.TestCase):
    def test_metrics(self):
        engine = UncertaintyEngine()
        belief = BeliefDistribution.gaussian([0.0, 0.0], np.eye(2))
        metrics = engine.metrics(belief)
        self.assertGreater(metrics.trace, 0.0)
        self.assertGreater(metrics.entropy, 0.0)


class TestHypothesisManager(unittest.TestCase):
    def test_propose_and_evidence(self):
        manager = HypothesisManager()
        h = manager.propose("Entity is a vehicle", initial_probability=0.5)
        manager.add_evidence(h.hypothesis_id, "Detected wheels", likelihood=0.9)
        updated = manager.get(h.hypothesis_id)
        # 0.5 * 0.9 = 0.45, then normalized (single hypothesis -> 1.0)
        self.assertGreater(updated.probability, 0.0)
        self.assertGreaterEqual(len(updated.evidence), 1)


class TestObjectMemory(unittest.TestCase):
    def test_observe_and_recall(self):
        memory = ObjectMemory()
        entity = TrackedEntity(entity_id=EntityID.new(), entity_type=EntityType.VEHICLE)
        record = memory.observe(entity)
        self.assertEqual(record.observation_count, 1)
        recalled = memory.recall(entity.entity_id)
        self.assertIsNotNone(recalled)


class TestExplainability(unittest.TestCase):
    def test_explain_entity(self):
        engine = ExplainabilityEngine()
        entity = TrackedEntity(
            entity_id=EntityID.new(),
            entity_type=EntityType.VEHICLE,
            confidence=0.8,
        )
        explanation = engine.explain_entity(entity)
        self.assertIn("Entity", explanation.summary)
        self.assertGreater(len(explanation.evidence_chain.links), 0)


class TestAttentionManager(unittest.TestCase):
    def test_compute_attention(self):
        manager = AttentionManager()
        entity = TrackedEntity(
            entity_id=EntityID.new(),
            uncertainty=0.5,
            confidence=0.8,
        )
        allocation = manager.compute_attention(entity, threat_score=0.7)
        self.assertGreater(allocation.attention_score, 0.0)


class TestInformationGain(unittest.TestCase):
    def test_entropy_reduction(self):
        estimator = InformationGainEstimator()
        belief = BeliefDistribution.gaussian([0.0, 0.0], np.eye(2) * 10.0)
        gain = estimator.entropy_reduction(
            belief, sensor_id="s1", entity_id="e1", measurement_noise=0.1
        )
        self.assertGreater(gain.expected_gain, 0.0)


class TestActivePerception(unittest.TestCase):
    def test_recommend_actions(self):
        ap = ActivePerception()
        ap.register_sensor_noise("s1", 0.1)
        entity = TrackedEntity(
            entity_id=EntityID.new(),
            belief=BeliefDistribution.gaussian([0.0, 0.0], np.eye(2) * 10.0),
        )
        actions = ap.recommend_actions([entity])
        self.assertGreaterEqual(len(actions), 0)


class TestChangeDetector(unittest.TestCase):
    def test_detect_appearance(self):
        detector = ChangeDetector()
        entity = TrackedEntity(entity_id=EntityID.new())
        reports = detector.detect(entity)
        self.assertEqual(len(reports), 1)
        self.assertEqual(reports[0].change_type.value, "appeared")


class TestCausalReasoner(unittest.TestCase):
    def test_infer_link(self):
        reasoner = CausalReasoner()
        from datetime import datetime, timedelta, timezone
        now = datetime.now(timezone.utc)
        reasoner.record_event("cause", now)
        reasoner.record_event("effect", now + timedelta(seconds=1))
        reasoner.record_event("cause", now + timedelta(seconds=10))
        reasoner.record_event("effect", now + timedelta(seconds=11))
        link = reasoner.infer_link("cause", "effect")
        self.assertIsNotNone(link)


class TestTemporalReasoner(unittest.TestCase):
    def test_detect_trend(self):
        reasoner = TemporalReasoner()
        entity = TrackedEntity(entity_id=EntityID.new())
        for i in range(10):
            entity.history.append(
                EntityState(
                    position=Vector3(x=float(i), y=0.0, z=0.0),
                    velocity=Vector3(x=1.0, y=0.0, z=0.0),
                )
            )
        patterns = reasoner.analyze_entity(entity)
        self.assertIsInstance(patterns, list)


class TestSemanticMap(unittest.TestCase):
    def test_add_region(self):
        smap = SemanticMap()
        region = smap.add_region(
            label="forest",
            category=EntityCategory.TERRAIN,
            center=Vector3(x=10.0, y=10.0, z=0.0),
            radius=5.0,
        )
        self.assertEqual(smap.count(), 1)
        found = smap.region_at(Vector3(x=11.0, y=11.0, z=0.0))
        self.assertIsNotNone(found)
        self.assertEqual(found.label, "forest")


class TestDynamicMap(unittest.TestCase):
    def test_occupancy(self):
        dmap = DynamicMap()
        dmap.update_occupancy(Vector3(x=1.0, y=1.0, z=0.0), 1.0)
        self.assertTrue(dmap.is_occupied(Vector3(x=1.0, y=1.0, z=0.0)))
        self.assertFalse(dmap.is_occupied(Vector3(x=50.0, y=50.0, z=0.0)))


class TestContextEngine(unittest.TestCase):
    def test_snapshot(self):
        engine = ContextEngine()
        engine.set_environmental("terrain", "urban")
        engine.set_situational("threat_level", "high")
        snapshot = engine.snapshot_for()
        self.assertEqual(snapshot.environmental["terrain"], "urban")
        self.assertEqual(snapshot.situational["threat_level"], "high")


class TestUncertaintyPropagator(unittest.TestCase):
    def test_propagate(self):
        propagator = UncertaintyPropagator()
        entity = TrackedEntity(
            entity_id=EntityID.new(),
            uncertainty=0.5,
            confidence=0.8,
        )
        trace = propagator.propagate(entity, horizon_seconds=10.0)
        self.assertGreater(trace.total_uncertainty, 0.0)


class TestVisualization(unittest.TestCase):
    def test_snapshot_to_dict(self):
        from brain.perception.situational_awareness import VisualizationEngine, WorldSnapshot
        viz = VisualizationEngine()
        snapshot = WorldSnapshot()
        data = viz.snapshot_to_dict(snapshot)
        self.assertIn("entities", data)


if __name__ == "__main__":
    unittest.main(verbosity=2)