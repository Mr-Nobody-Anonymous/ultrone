#!/usr/bin/env python3
"""Benchmark suite for the Situational Awareness System."""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import asyncio
import time
import numpy as np

from brain.perception.situational_awareness import (
    AwarenessEngine,
    BeliefDistribution,
    EntityID,
    EntityState,
    EntityType,
    EntityCategory,
    SensorFusionEngine,
    SensorMeasurement,
    Observation,
    CovarianceMatrix,
    TrackedEntity,
    Vector3,
    WorldModel,
    SceneGraph,
    TrajectoryPredictor,
    EventPredictor,
    ThreatAssessor,
    AnomalyDetector,
    IntentEstimator,
    AttentionManager,
    ActivePerception,
    InformationGainEstimator,
    UncertaintyEngine,
    ConfidenceEngine,
    HypothesisManager,
    ObjectMemory,
    TemporalReasoner,
    CausalReasoner,
    SemanticMap,
    DynamicMap,
    ChangeDetector,
    ContextEngine,
    UncertaintyPropagator,
    ExplainabilityEngine,
    VisualizationEngine,
    WorldStateCache,
    ObservationHistory,
    EntityTracker,
    ObservationValidator,
    SensorRegistry,
    SensorSpecification,
    SensorType,
    BeliefStateEstimator,
)


def benchmark(name, fn, iterations=100):
    """Run a benchmark and print results."""
    start = time.perf_counter()
    for _ in range(iterations):
        fn()
    elapsed = time.perf_counter() - start
    per_op = elapsed / iterations * 1000  # ms
    print(f"  {name}: {per_op:.3f} ms/op ({iterations} ops in {elapsed:.3f}s)")
    return per_op


def make_entity():
    return TrackedEntity(
        entity_id=EntityID.new(),
        entity_type=EntityType.VEHICLE,
        category=EntityCategory.FRIEND,
        state=EntityState(
            position=Vector3(x=1.0, y=2.0, z=0.0),
            velocity=Vector3(x=5.0, y=0.0, z=0.0),
        ),
        confidence=0.8,
        belief=BeliefDistribution.gaussian([1.0, 2.0, 0.0], np.eye(3) * 0.1),
    )


def make_observation():
    return Observation(
        sensor_id="cam1",
        measurement=SensorMeasurement(
            value=[1.0, 2.0, 3.0],
            covariance=CovarianceMatrix.eye(3, scale=0.1),
        ),
        confidence=0.8,
    )


def run_benchmarks():
    print("=" * 60)
    print("SITUATIONAL AWARENESS BENCHMARKS")
    print("=" * 60)

    # Core types
    print("\n[Core Types]")
    benchmark("EntityID.new", lambda: EntityID.new(), 1000)
    benchmark("Vector3.distance", lambda: Vector3(x=1.0, y=2.0, z=3.0).distance_to(Vector3()), 1000)
    benchmark("BeliefDistribution.entropy", lambda: BeliefDistribution.gaussian([0.0, 0.0], np.eye(2)).entropy(), 1000)

    # World model
    print("\n[World Model]")
    model = WorldModel()
    benchmark("create_entity", lambda: model.create_entity(
        entity_type=EntityType.VEHICLE, category=EntityCategory.FRIEND
    ), 100)
    benchmark("snapshot", lambda: model.snapshot(), 100)

    # Sensor fusion
    print("\n[Sensor Fusion]")
    engine = SensorFusionEngine()
    obs1 = make_observation()
    obs2 = Observation(
        sensor_id="radar1",
        measurement=SensorMeasurement(value=[1.1, 2.1, 3.1], covariance=CovarianceMatrix.eye(3, scale=0.2)),
        confidence=0.7,
    )
    for strategy in engine.available_strategies:
        benchmark(f"fuse_{strategy}", lambda s=strategy: engine.fuse([obs1, obs2], strategy=s), 50)

    # Belief state
    print("\n[Belief State]")
    estimator = BeliefStateEstimator()
    eid = EntityID.new()
    estimator.initialize_gaussian(eid, [0.0, 0.0, 0.0], np.eye(3) * 10.0)
    benchmark("gaussian_update", lambda: estimator.gaussian_update(eid, [1.0, 1.0, 1.0], np.eye(3) * 0.1), 100)

    # Scene graph
    print("\n[Scene Graph]")
    graph = SceneGraph()
    entities = [make_entity() for _ in range(10)]
    for e in entities:
        graph.add_entity(e)
    benchmark("add_entity", lambda: graph.add_entity(make_entity()), 100)
    benchmark("stats", lambda: graph.stats(), 100)

    # Trajectory prediction
    print("\n[Trajectory Prediction]")
    predictor = TrajectoryPredictor()
    entity = make_entity()
    benchmark("predict", lambda: predictor.predict(entity), 100)

    # Event prediction
    print("\n[Event Prediction]")
    event_predictor = EventPredictor()
    event_predictor.add_proximity_rule("approach", threshold_distance=10.0)
    benchmark("predict_entity", lambda: event_predictor.predict_entity(entity), 100)

    # Threat assessment
    print("\n[Threat Assessment]")
    assessor = ThreatAssessor()
    assessor.add_protected_asset(Vector3(x=0.0, y=0.0, z=0.0))
    benchmark("assess", lambda: assessor.assess(entity), 100)

    # Anomaly detection
    print("\n[Anomaly Detection]")
    detector = AnomalyDetector()
    benchmark("analyze_entity", lambda: detector.analyze_entity(entity), 100)

    # Intent estimation
    print("\n[Intent Estimation]")
    intent = IntentEstimator()
    intent.add_protected_asset(Vector3(x=0.0, y=0.0, z=0.0))
    benchmark("estimate", lambda: intent.estimate(entity), 100)

    # Attention
    print("\n[Attention]")
    attention = AttentionManager()
    benchmark("compute_attention", lambda: attention.compute_attention(entity, threat_score=0.5), 100)

    # Information gain
    print("\n[Information Gain]")
    ig = InformationGainEstimator()
    benchmark("entropy_reduction", lambda: ig.entropy_reduction(entity.belief, sensor_id="s1", entity_id="e1"), 100)

    # Active perception
    print("\n[Active Perception]")
    ap = ActivePerception()
    ap.register_sensor_noise("s1", 0.1)
    benchmark("recommend_actions", lambda: ap.recommend_actions([entity]), 100)

    # Uncertainty
    print("\n[Uncertainty]")
    unc = UncertaintyEngine()
    benchmark("metrics", lambda: unc.metrics(entity.belief), 100)

    # Confidence
    print("\n[Confidence]")
    conf = ConfidenceEngine()
    benchmark("aggregate", lambda: conf.aggregate([0.8, 0.9, 0.7, 0.6]), 100)

    # Hypothesis
    print("\n[Hypothesis]")
    hyp = HypothesisManager()
    h = hyp.propose("Test hypothesis", initial_probability=0.5)
    benchmark("add_evidence", lambda: hyp.add_evidence(h.hypothesis_id, "evidence", likelihood=0.9), 100)

    # Object memory
    print("\n[Object Memory]")
    mem = ObjectMemory()
    benchmark("observe", lambda: mem.observe(entity), 100)

    # Temporal reasoning
    print("\n[Temporal Reasoning]")
    temporal = TemporalReasoner()
    for i in range(10):
        entity.history.append(EntityState(position=Vector3(x=float(i), y=0.0, z=0.0)))
    benchmark("analyze_entity", lambda: temporal.analyze_entity(entity), 100)

    # Causal reasoning
    print("\n[Causal Reasoning]")
    causal = CausalReasoner()
    benchmark("record_event", lambda: causal.record_event("event1"), 100)

    # Semantic map
    print("\n[Semantic Map]")
    smap = SemanticMap()
    benchmark("add_region", lambda: smap.add_region(
        label="forest", category=EntityCategory.TERRAIN,
        center=Vector3(x=10.0, y=10.0, z=0.0), radius=5.0
    ), 100)

    # Dynamic map
    print("\n[Dynamic Map]")
    dmap = DynamicMap()
    benchmark("update_occupancy", lambda: dmap.update_occupancy(Vector3(x=1.0, y=1.0, z=0.0), 1.0), 100)

    # Change detection
    print("\n[Change Detection]")
    change = ChangeDetector()
    benchmark("detect", lambda: change.detect(entity), 100)

    # Context
    print("\n[Context]")
    ctx = ContextEngine()
    benchmark("snapshot_for", lambda: ctx.snapshot_for(entity), 100)

    # Uncertainty propagation
    print("\n[Uncertainty Propagation]")
    prop = UncertaintyPropagator()
    benchmark("propagate", lambda: prop.propagate(entity, horizon_seconds=10.0), 100)

    # Explainability
    print("\n[Explainability]")
    expl = ExplainabilityEngine()
    benchmark("explain_entity", lambda: expl.explain_entity(entity), 100)

    # Visualization
    print("\n[Visualization]")
    viz = VisualizationEngine()
    snapshot = model.snapshot()
    benchmark("snapshot_to_dict", lambda: viz.snapshot_to_dict(snapshot), 100)

    # Cache
    print("\n[Cache]")
    cache = WorldStateCache()
    benchmark("put_entity", lambda: cache.put_entity(entity), 100)

    # Observation history
    print("\n[Observation History]")
    history = ObservationHistory()
    obs = make_observation()
    benchmark("add", lambda: history.add(obs), 100)

    # Entity tracker
    print("\n[Entity Tracker]")
    tracker = EntityTracker()
    tracker.create_track(obs, entity)
    benchmark("associate", lambda: tracker.associate(obs), 100)

    # Observation validator
    print("\n[Observation Validator]")
    validator = ObservationValidator()
    benchmark("validate", lambda: validator.validate(obs), 100)

    # Sensor registry
    print("\n[Sensor Registry]")
    registry = SensorRegistry()
    spec = SensorSpecification(sensor_id="bench1", sensor_type=SensorType.CAMERA)
    registry.register(spec)
    benchmark("get", lambda: registry.get("bench1"), 100)

    # Full engine tick
    print("\n[Full Engine]")
    async def run_engine_tick():
        engine = AwarenessEngine()
        for i in range(10):
            await engine.ingest_observation(
                sensor_id="cam1",
                value=[float(i), float(i), 0.0],
                confidence=0.8,
            )
        await engine.tick()
        await engine.close()

    start = time.perf_counter()
    asyncio.run(run_engine_tick())
    elapsed = time.perf_counter() - start
    print(f"  full_tick: {elapsed * 1000:.3f} ms/op")

    print("\n" + "=" * 60)
    print("BENCHMARKS COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    run_benchmarks()
