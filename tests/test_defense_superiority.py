# Copyright (c) Ultrone Contributors. All rights reserved.
"""Comprehensive verification suite for Next-Gen Multi-Domain Defense Capabilities.

Verifies superiority over Palantir (Gotham/Foundry/AIP/Apollo) and Anduril (Lattice OS/Menace):
1. Multi-Domain Defense Ontology & Multi-INT Data Graph (Air, Space, Maritime, Land, Cyber, EW).
2. Multi-Hypothesis Track Correlation & Threat Scoring.
3. Decentralized Byzantine-Resilient CRDT World Mesh for DDIL Environments.
4. Dynamic Sensor-to-Effector Allocator with Multi-Objective Pareto Optimization.
5. Formal Rules of Engagement (ROE) & Law of Armed Conflict (LOAC) Verification Engine.
6. Cognitive Electronic Warfare (EW), Anti-Spoofing & Decoy Filtering.
7. Real-Time Game-Theoretic Coevolution & Predictive Simulation (AlphaWarfare).
8. Cockpit REST API Defense Endpoints.
"""
from __future__ import annotations

import time
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from apps.api.routers.cockpit import router as cockpit_router
from packages.core.ontology.defense_ontology import (
    Affiliation,
    KinematicState,
    MultiHypothesisTracker,
    MultiIntTrack,
    SensorModality,
    TrackObservation,
    WarfightingDomain,
)
from packages.runtime.crdt_mesh import (
    ByzantinePhysicalFilter,
    CRDTEntityState,
    DecentralizedWorldMesh,
    SyncDelta,
    VectorClock,
)
from packages.cognition.kill_chain import (
    EffectorAsset,
    EffectorType,
    KillChainStage,
    SensorToEffectorAllocator,
)
from packages.safety.roe import (
    EffectorLease,
    RulesOfEngagementEngine,
)
from packages.cognition.electronic_warfare import (
    CognitiveAntiSpoofEngine,
    EmconState,
    GpsTelemetry,
)
from packages.cognition.adversarial_wargame import (
    BattlefieldState,
    PredictiveWargameEngine,
    TacticalActionType,
    UnitState,
)


@pytest.fixture(scope="module")
def api_client():
    app = FastAPI(title="Defense API Test")
    app.include_router(cockpit_router)
    return TestClient(app)


# ── 1. Multi-Domain Defense Ontology & MHT ──────────────────────────────────

def test_multi_domain_ontology_track_creation_and_domains():
    tracker = MultiHypothesisTracker(correlation_gate_nm=10.0)
    now = time.time()

    # Space track
    obs_space = TrackObservation(
        observation_id="OBS-SP-01",
        modality=SensorModality.RADAR,
        sensor_id="EARLY_WARNING_RADAR",
        lat=30.0,
        lon=35.0,
        altitude_m=150000.0,
        timestamp=now,
    )
    t_space = tracker.ingest_observation(obs_space)
    assert t_space.domain == WarfightingDomain.SPACE

    # Air track
    obs_air = TrackObservation(
        observation_id="OBS-AIR-01",
        modality=SensorModality.RADAR,
        sensor_id="AESA_NORTH",
        lat=32.0,
        lon=35.0,
        altitude_m=5000.0,
        timestamp=now,
    )
    t_air = tracker.ingest_observation(obs_air)
    assert t_air.domain == WarfightingDomain.AIR

    # Subsurface track
    obs_sub = TrackObservation(
        observation_id="OBS-SUB-01",
        modality=SensorModality.ACOUSTIC,
        sensor_id="HYDROPHONE_ARRAY_01",
        lat=32.5,
        lon=34.5,
        altitude_m=-50.0,
        timestamp=now,
    )
    t_sub = tracker.ingest_observation(obs_sub)
    assert t_sub.domain == WarfightingDomain.MARITIME_SUBSURFACE


def test_mht_track_fusion_and_pid_confidence_elevation():
    tracker = MultiHypothesisTracker(correlation_gate_nm=15.0)
    now = time.time()

    # Observation 1 from Radar
    obs1 = TrackObservation(
        observation_id="OBS-1",
        modality=SensorModality.RADAR,
        sensor_id="RADAR-A",
        lat=32.0,
        lon=35.0,
        altitude_m=3000.0,
        timestamp=now,
    )
    t1 = tracker.ingest_observation(obs1)
    initial_pid = t1.pid_confidence

    # Corroborating Observation 2 from EO/IR at close coordinate
    obs2 = TrackObservation(
        observation_id="OBS-2",
        modality=SensorModality.EO_IR,
        sensor_id="FLIR-B",
        lat=32.02,
        lon=35.01,
        altitude_m=3050.0,
        timestamp=now + 1.0,
    )
    t2 = tracker.ingest_observation(obs2)

    # Must correlate to the same track and increase confidence
    assert t1.track_id == t2.track_id
    assert len(t2.observations) == 2
    assert t2.pid_confidence > initial_pid


def test_threat_evaluation_heading_towards_hva():
    tracker = MultiHypothesisTracker(
        hva_positions=[(32.0, 34.8, "HVA_ALPHA")]
    )
    # Track heading straight toward HVA (from 32.5, 34.8 heading South 180 deg)
    obs = TrackObservation(
        observation_id="OBS-THREAT",
        modality=SensorModality.RADAR,
        sensor_id="RADAR-A",
        lat=32.3,
        lon=34.8,
        altitude_m=2000.0,
        timestamp=time.time(),
    )
    track = tracker.ingest_observation(obs)
    track.affiliation = Affiliation.HOSTILE
    track.kinematics.heading_deg = 180.0
    track.kinematics.speed_knots = 500.0
    tracker._evaluate_threat(track)

    assert track.threat_score >= 0.70


# ── 2. Decentralized CRDT World Mesh ────────────────────────────────────────

def test_crdt_vector_clock_causality():
    vc1 = VectorClock()
    vc1.increment("NODE_A")
    vc1.increment("NODE_B")

    vc2 = VectorClock()
    vc2.increment("NODE_A")

    assert vc1.is_causally_newer(vc2)
    assert not vc2.is_causally_newer(vc1)

    vc2.merge(vc1)
    assert vc2.clock["NODE_B"] == 1


def test_crdt_gossip_sync_and_convergence():
    node_a = DecentralizedWorldMesh(node_id="NODE_A")
    node_b = DecentralizedWorldMesh(node_id="NODE_B")

    # Node A creates entity
    node_a.upsert_local_entity("TARGET-ALPHA", {"lat": 32.1, "lon": 34.9, "threat": 0.85})
    delta_a = node_a.generate_delta()

    # Node B ingests gossip delta from Node A
    res = node_b.receive_delta(delta_a)
    assert res["accepted"] is True
    assert res["applied_entities"] == 1
    assert "TARGET-ALPHA" in node_b.entities
    assert node_b.entities["TARGET-ALPHA"].properties["threat"] == 0.85


def test_byzantine_filter_rejects_impossible_teleportation():
    node_a = DecentralizedWorldMesh(node_id="NODE_A")
    node_b = DecentralizedWorldMesh(node_id="NODE_B")

    # Baseline position at time T
    now = time.time()
    e_clean = node_a.upsert_local_entity("TARGET-X", {"lat": 32.0, "lon": 34.0})
    e_clean.wall_time = now
    node_b.receive_delta(node_a.generate_delta())

    # Hostile peer tries to inject impossible teleportation: 1000 nm in 1 second (> 3600000 knots)
    e_spoofed = CRDTEntityState(
        entity_id="TARGET-X",
        owner_node="ROGUE_NODE",
        properties={"lat": 48.0, "lon": 15.0},
        vector_clock=VectorClock({"ROGUE_NODE": 10}),
        wall_time=now + 1.0,
    )
    delta_rogue = SyncDelta(
        sender_node_id="ROGUE_NODE",
        sequence_num=1,
        entities=[e_spoofed],
        timestamp=now + 1.0,
    )
    delta_rogue.mac = delta_rogue.compute_mac(node_b.shared_secret)

    res = node_b.receive_delta(delta_rogue)
    assert res["quarantined_entities"] == 1
    assert len(node_b.rejected_updates) == 1
    assert "teleportation detected" in node_b.rejected_updates[0]["reason"]
    # Node B preserves legitimate local position
    assert node_b.entities["TARGET-X"].properties["lat"] == 32.0


# ── 3. Sensor-to-Effector Allocator ─────────────────────────────────────────

def test_sensor_to_effector_pareto_matching():
    allocator = SensorToEffectorAllocator()

    # Threat track: incoming hostile UAV swarm
    track = MultiIntTrack(
        track_id="TRK-DRONE-01",
        domain=WarfightingDomain.AIR,
        affiliation=Affiliation.HOSTILE,
        entity_class="UAV_SWARM",
        kinematics=KinematicState(lat=32.25, lon=35.05, speed_knots=120.0),
        threat_score=0.88,
        pid_confidence=0.92,
    )

    # Effectors: 1 cheap soft-kill RF Jammer nearby + 1 expensive kinetic missile
    rf_jammer = EffectorAsset(
        effector_id="EFF-JAMMER-01",
        name="AESA Jammer",
        effector_type=EffectorType.SOFT_RF_JAMMER,
        domain=WarfightingDomain.ELECTROMAGNETIC_SPECTRUM,
        lat=32.20,
        lon=35.00,
        range_max_nm=25.0,
        speed_max_knots=0.0,
        cost_usd=10.0,
        is_soft_kill=True,
    )
    kinetic = EffectorAsset(
        effector_id="EFF-MISSILE-01",
        name="Kinetic Interceptor",
        effector_type=EffectorType.HARD_KINETIC_INTERCEPTOR,
        domain=WarfightingDomain.AIR,
        lat=32.00,
        lon=34.80,
        range_max_nm=60.0,
        speed_max_knots=600.0,
        cost_usd=120000.0,
        is_soft_kill=False,
    )

    plans = allocator.compute_optimal_assignments([track], [rf_jammer, kinetic])
    assert len(plans) == 1
    plan = plans[0]
    # Should select the soft-kill jammer due to zero collateral risk, low cost, and high drone susceptibility
    assert plan.effector_id == "EFF-JAMMER-01"
    assert plan.target_track_id == "TRK-DRONE-01"
    assert plan.stage == KillChainStage.TARGET


# ── 4. Rules of Engagement & LOAC Verification ──────────────────────────────

def test_roe_loac_distinction_failure_on_low_pid():
    roe = RulesOfEngagementEngine(min_pid_confidence_kinetic=0.85)

    track = MultiIntTrack(
        track_id="TRK-AMBIGUOUS-01",
        domain=WarfightingDomain.AIR,
        affiliation=Affiliation.SUSPECT,
        kinematics=KinematicState(lat=32.2, lon=35.0),
        pid_confidence=0.55,  # Low PID confidence
    )
    plan = type("MockPlan", (), {
        "effector_type": EffectorType.HARD_KINETIC_INTERCEPTOR,
        "effector_id": "EFF-KINETIC-01",
        "collateral_damage_risk": 0.05,
    })()

    allowed, lease_id, reason = roe.verify_engagement(track, plan)
    assert allowed is False
    assert "LOAC DISTINCTION FAILURE" in reason
    assert lease_id is None


def test_roe_no_strike_list_geofence_protection():
    roe = RulesOfEngagementEngine()

    # Track located exactly inside Al-Shifa Hospital Complex (NSL-001: 31.52, 34.45)
    track = MultiIntTrack(
        track_id="TRK-HOSPITAL-VICINITY",
        domain=WarfightingDomain.LAND,
        affiliation=Affiliation.HOSTILE,
        kinematics=KinematicState(lat=31.5205, lon=34.4505),
        pid_confidence=0.99,
        anti_spoof_confidence=1.0,
    )
    plan = type("MockPlan", (), {
        "effector_type": EffectorType.HARD_KINETIC_INTERCEPTOR,
        "effector_id": "EFF-01",
        "collateral_damage_risk": 0.02,
    })()

    allowed, lease_id, reason = roe.verify_engagement(track, plan)
    assert allowed is False
    assert "NO-STRIKE LIST VIOLATION" in reason


def test_roe_human_on_the_loop_veto():
    roe = RulesOfEngagementEngine()

    track = MultiIntTrack(
        track_id="TRK-VALID-TARGET",
        domain=WarfightingDomain.AIR,
        affiliation=Affiliation.HOSTILE,
        kinematics=KinematicState(lat=32.8, lon=35.5),
        pid_confidence=0.95,
        anti_spoof_confidence=1.0,
    )
    plan = type("MockPlan", (), {
        "effector_type": EffectorType.HARD_KINETIC_INTERCEPTOR,
        "effector_id": "EFF-01",
        "collateral_damage_risk": 0.04,
    })()

    allowed, lease_id, _ = roe.verify_engagement(track, plan)
    assert allowed is True
    assert lease_id is not None
    assert roe.issued_leases[lease_id].is_valid() is True

    # Operator vetoes engagement
    aborted = roe.record_human_veto(lease_id, "CDR_SMITH", "Civilian vehicle entered impact radius")
    assert aborted is True
    assert roe.issued_leases[lease_id].is_valid() is False
    assert len(roe.veto_log) == 1


# ── 5. Cognitive Electronic Warfare & Anti-Spoofing ─────────────────────────

def test_anti_spoofing_detects_gps_teleportation():
    engine = CognitiveAntiSpoofEngine()
    now = time.time()

    # Initial fix
    gps1 = GpsTelemetry(lat=32.0, lon=34.0, altitude_m=100.0, ground_speed_knots=50.0, satellites_tracked=10, timestamp=now)
    engine.verify_gps_integrity(gps1)

    # Malicious GPS spoof fix 1 second later jumping 100 nautical miles
    gps2 = GpsTelemetry(lat=33.5, lon=34.0, altitude_m=100.0, ground_speed_knots=50.0, satellites_tracked=10, timestamp=now + 1.0)
    is_auth, conf, diag = engine.verify_gps_integrity(gps2)

    assert is_auth is False
    assert "teleportation" in diag.lower()
    assert conf < 0.20


def test_anti_spoofing_detects_radar_decoy():
    engine = CognitiveAntiSpoofEngine()

    # Radar reports large RCS (12 m2) but FLIR thermal sensor shows ambient temperature (zero engine heat)
    is_real, conf, diag = engine.verify_target_signature(
        radar_rcs_m2=12.0,
        flir_thermal_celsius=21.0,
        ambient_celsius=20.0,
    )
    assert is_real is False
    assert "DECOY SIGNATURE" in diag


def test_emcon_scheduling():
    engine = CognitiveAntiSpoofEngine()
    assert engine.set_emcon_policy("CRITICAL") == EmconState.SILENT
    assert engine.set_emcon_policy("ELEVATED") == EmconState.RESTRICTED
    assert engine.set_emcon_policy("NOMINAL") == EmconState.TACTICAL


# ── 6. Predictive Adversarial Wargame (MCTS) ────────────────────────────────

def test_predictive_wargame_counter_tactics():
    engine = PredictiveWargameEngine(simulation_depth=2, rollout_count=20, seed=123)

    blue = [UnitState("B1", "BLUE", lat=32.0, lon=34.8, health_pct=100.0, ammo_rounds=10)]
    red = [UnitState("R1", "RED", lat=32.2, lon=34.8, health_pct=90.0, ammo_rounds=8)]
    state = BattlefieldState(blue_units=blue, red_units=red)

    recs = engine.synthesize_counter_tactics(state)
    assert len(recs) > 0
    # Best action has positive win rate
    assert recs[0].predicted_win_rate > 0.0
    assert recs[0].action in TacticalActionType


# ── 7. Cockpit REST API Defense Endpoints ───────────────────────────────────

def test_api_defense_endpoints(api_client):
    # COP
    res_cop = api_client.get("/api/cockpit/defense/cop")
    assert res_cop.status_code == 200
    data_cop = res_cop.json()
    assert "total_tracks" in data_cop
    assert "tracks" in data_cop
    assert len(data_cop["tracks"]) > 0

    # CRDT World Mesh
    res_mesh = api_client.get("/api/cockpit/defense/mesh")
    assert res_mesh.status_code == 200
    data_mesh = res_mesh.json()
    assert "node_id" in data_mesh
    assert "entities" in data_mesh

    # Kill Chain
    res_kc = api_client.get("/api/cockpit/defense/kill-chain")
    assert res_kc.status_code == 200
    data_kc = res_kc.json()
    assert "plans" in data_kc
    assert "effectors" in data_kc

    # ROE
    res_roe = api_client.get("/api/cockpit/defense/roe")
    assert res_roe.status_code == 200
    data_roe = res_roe.json()
    assert data_roe["status"] == "ENFORCED"
    assert "no_strike_list" in data_roe

    # Anti-Spoofing
    res_as = api_client.get("/api/cockpit/defense/anti-spoofing")
    assert res_as.status_code == 200
    data_as = res_as.json()
    assert "gps_integrity" in data_as
    assert "emcon_state" in data_as

    # Wargame
    res_wg = api_client.get("/api/cockpit/defense/wargame")
    assert res_wg.status_code == 200
    data_wg = res_wg.json()
    assert "recommendations" in data_wg
    assert len(data_wg["recommendations"]) > 0

    # Overview integration
    res_ov = api_client.get("/api/cockpit/overview")
    assert res_ov.status_code == 200
    data_ov = res_ov.json()
    assert "defense" in data_ov
    assert data_ov["defense"]["roe_enforced"] is True


# ── 8. Deep Edge Case & Boundary Verification ───────────────────────────────

def test_polygonal_nsl_geofencing_and_altitude_boundary():
    """Verify non-convex polygon ray-casting and 3D altitude envelope."""
    roe = RulesOfEngagementEngine()

    # The UN Humanitarian Safe Corridor polygon in roe is around lat 31.40, lon 34.35, alt <= 4500m
    # Inside polygon and below 4500m
    track_inside = MultiIntTrack(
        track_id="TRK-NSL-IN",
        domain=WarfightingDomain.AIR,
        affiliation=Affiliation.HOSTILE,
        kinematics=KinematicState(lat=31.41, lon=34.36, altitude_m=2000.0, speed_knots=200.0, heading_deg=90.0),
        pid_confidence=0.95,
        threat_score=0.85,
    )
    plan = type("EngagementPlan", (), {
        "effector_id": "EFF-KINETIC-1",
        "effector_type": type("EffType", (), {"value": "HARD_KINETIC_INTERCEPTOR"})(),
        "collateral_damage_risk": 0.05,
    })()

    ok, lease_id, reason = roe.verify_engagement(track_inside, plan)
    assert ok is False
    assert "NO-STRIKE LIST VIOLATION" in reason
    assert "UN Humanitarian Safe Corridor" in reason

    # Inside polygon lat/lon, but flying at 8000m (above 4500m max_altitude_m ceiling)
    track_overflight = MultiIntTrack(
        track_id="TRK-NSL-OVER",
        domain=WarfightingDomain.AIR,
        affiliation=Affiliation.HOSTILE,
        kinematics=KinematicState(lat=31.41, lon=34.36, altitude_m=8000.0, speed_knots=500.0, heading_deg=90.0),
        pid_confidence=0.95,
        threat_score=0.85,
    )
    ok_over, lease_over, reason_over = roe.verify_engagement(track_overflight, plan)
    assert ok_over is True
    assert lease_over is not None


def test_kill_chain_allocator_soft_kill_fallback_on_roe_rejection():
    """Ensure allocator does NOT abandon target if kinetic effector fails ROE, falling back to soft-kill."""
    roe = RulesOfEngagementEngine()
    allocator = SensorToEffectorAllocator()

    # Target has PID 0.70 (sufficient for soft-kill >= 0.55, but insufficient for kinetic >= 0.85)
    target = MultiIntTrack(
        track_id="TRK-MED-PID",
        domain=WarfightingDomain.AIR,
        affiliation=Affiliation.HOSTILE,
        entity_class="UAV_SWARM",
        kinematics=KinematicState(lat=31.8, lon=34.6, altitude_m=1000.0, speed_knots=80.0, heading_deg=45.0),
        pid_confidence=0.70,
        threat_score=0.80,
    )

    # Two effectors: Kinetic missile (higher raw score) and Soft-kill jammer
    kinetic_eff = EffectorAsset(
        effector_id="EFF-MISSILE",
        name="Kinetic Interceptor Block IV",
        effector_type=EffectorType.HARD_KINETIC_INTERCEPTOR,
        domain=WarfightingDomain.AIR,
        lat=31.8,
        lon=34.6,
        range_max_nm=50.0,
        cost_usd=800000.0,
        is_soft_kill=False,
    )
    soft_eff = EffectorAsset(
        effector_id="EFF-RF-JAMMER",
        name="Tactical AESA EW Jammer",
        effector_type=EffectorType.SOFT_RF_JAMMER,
        domain=WarfightingDomain.ELECTROMAGNETIC_SPECTRUM,
        lat=31.8,
        lon=34.6,
        range_max_nm=50.0,
        cost_usd=50000.0,
        is_soft_kill=True,
    )

    plans = allocator.compute_optimal_assignments([target], [kinetic_eff, soft_eff], roe_verifier=roe)
    # Target MUST be assigned rather than dropped!
    assert len(plans) == 1
    assert plans[0].target_track_id == "TRK-MED-PID"
    # Assigned effector must be the soft-kill jammer because kinetic was blocked by PID distinction!
    assert plans[0].effector_id == "EFF-RF-JAMMER"
    assert plans[0].authorized_by_roe is True
    assert plans[0].roe_lease_id is not None


def test_byzantine_filter_dt_zero_multi_location_and_coordinate_bounds():
    """Verify Byzantine filter catches dt=0 teleportations and out-of-bounds coordinates."""
    filter = ByzantinePhysicalFilter(max_speed_knots=3000.0)
    now = time.time()

    curr = CRDTEntityState(
        entity_id="ENT-01",
        owner_node="NODE-A",
        properties={"lat": 32.0, "lon": 34.8},
        vector_clock=VectorClock(),
        wall_time=now,
    )

    # 1. dt == 0.0 with identical position is accepted as concurrent update
    prop_same = CRDTEntityState(
        entity_id="ENT-01",
        owner_node="NODE-B",
        properties={"lat": 32.0, "lon": 34.8},
        vector_clock=VectorClock(),
        wall_time=now,
    )
    ok_same, _ = filter.validate_transition(curr, prop_same)
    assert ok_same is True

    # 2. dt == 0.0 with divergent position is rejected as instantaneous teleportation
    prop_teleport_dt0 = CRDTEntityState(
        entity_id="ENT-01",
        owner_node="NODE-B",
        properties={"lat": 40.0, "lon": 50.0},
        vector_clock=VectorClock(),
        wall_time=now,
    )
    ok_dt0, reason_dt0 = filter.validate_transition(curr, prop_teleport_dt0)
    assert ok_dt0 is False
    assert "simultaneous multi-location" in reason_dt0

    # 3. Existing entity proposed update with invalid coordinate bounds is rejected
    prop_invalid_lat = CRDTEntityState(
        entity_id="ENT-01",
        owner_node="NODE-B",
        properties={"lat": 999.0, "lon": 34.8},
        vector_clock=VectorClock(),
        wall_time=now + 1.0,
    )
    ok_inv, reason_inv = filter.validate_transition(curr, prop_invalid_lat)
    assert ok_inv is False
    assert "Invalid latitude" in reason_inv


def test_anti_spoofing_timestamp_inversion_and_drift_decoy():
    """Verify anti-spoofing rejects timestamp regressions and flags wind-drifting balloons."""
    engine = CognitiveAntiSpoofEngine()
    now = time.time()

    gps1 = GpsTelemetry(lat=32.0, lon=34.8, altitude_m=100.0, ground_speed_knots=100.0, satellites_tracked=10, timestamp=now)
    ok1, _, _ = engine.verify_gps_integrity(gps1)
    assert ok1 is True

    # Timestamp regression (replay attack)
    gps_regressed = GpsTelemetry(lat=32.01, lon=34.81, altitude_m=100.0, ground_speed_knots=100.0, satellites_tracked=10, timestamp=now - 5.0)
    ok_reg, conf_reg, reason_reg = engine.verify_gps_integrity(gps_regressed)
    assert ok_reg is False
    assert "TIMESTAMP INVERSION" in reason_reg

    # Wind-drifting passive balloon decoy
    is_real, conf, reason = engine.verify_target_signature(
        radar_rcs_m2=8.0,
        flir_thermal_celsius=20.5,
        ambient_celsius=20.0,
        target_speed_knots=14.0,
        ambient_wind_knots=13.0,
    )
    assert is_real is False
    assert "PASSIVE DECOY BALLOON" in reason


def test_predictive_wargame_numerical_stability():
    """Verify wargame handles extreme payoffs without math range OverflowError."""
    from packages.cognition.adversarial_wargame.predictive_wargame import _safe_sigmoid

    # Test extreme values
    assert _safe_sigmoid(1000000.0) == 1.0
    assert _safe_sigmoid(-1000000.0) == pytest.approx(0.0, abs=1e-10)

    engine = PredictiveWargameEngine(simulation_depth=1, rollout_count=5, seed=42)
    # Asymmetric battle: Red has no units
    blue = [UnitState("B1", "BLUE", lat=32.0, lon=34.8, health_pct=100.0, ammo_rounds=10)]
    state_asym = BattlefieldState(blue_units=blue, red_units=[])
    recs = engine.synthesize_counter_tactics(state_asym)
    assert len(recs) > 0
    assert 0.0 <= recs[0].predicted_win_rate <= 1.0


def test_antimeridian_and_polar_navigation_in_byzantine_and_anti_spoof():
    """Verify spherical Haversine prevents false teleportation/spoof alarms across 180° antimeridian."""
    filter = ByzantinePhysicalFilter(max_speed_knots=3500.0)
    now = time.time()

    # Aircraft crossing from 179.99°E to -179.99°W in 10s at 20°N (~1.13 nm -> ~406 kts)
    e1 = CRDTEntityState("PACIFIC-FLIGHT-01", "NODE-US", {"lat": 20.0, "lon": 179.99}, VectorClock(), wall_time=now)
    e2 = CRDTEntityState("PACIFIC-FLIGHT-01", "NODE-US", {"lat": 20.0, "lon": -179.99}, VectorClock(), wall_time=now + 10.0)

    ok_byz, reason_byz = filter.validate_transition(e1, e2)
    assert ok_byz is True, f"Antimeridian crossing falsely rejected by Byzantine filter: {reason_byz}"

    # Verify anti-spoof engine also accepts antimeridian crossing without false teleportation alarm
    ew = CognitiveAntiSpoofEngine()
    g1 = GpsTelemetry(lat=20.0, lon=179.99, altitude_m=10000.0, ground_speed_knots=410.0, satellites_tracked=12, timestamp=now)
    ok_g1, _, _ = ew.verify_gps_integrity(g1)
    assert ok_g1 is True

    g2 = GpsTelemetry(lat=20.0, lon=-179.99, altitude_m=10000.0, ground_speed_knots=410.0, satellites_tracked=12, timestamp=now + 10.0)
    ok_g2, conf_g2, reason_g2 = ew.verify_gps_integrity(g2)
    assert ok_g2 is True, f"Antimeridian crossing falsely flagged as spoof by EW engine: {reason_g2}"
    assert conf_g2 >= 0.90


def test_crdt_mesh_out_of_order_gossip_no_false_quarantine():
    """Ensure delayed/out-of-order gossip packets in contested tactical networks are superseded rather than falsely quarantined."""
    mesh_b = DecentralizedWorldMesh(node_id="NODE-B")
    now = time.time()

    # Local entity on Node B updated at t = now + 1.0s
    mesh_b.entities["TRK-RECON-1"] = CRDTEntityState(
        entity_id="TRK-RECON-1",
        owner_node="NODE-B",
        properties={"lat": 32.5, "lon": 34.8, "speed": 200.0},
        vector_clock=VectorClock({"NODE-B": 3}),
        wall_time=now + 1.0,
    )

    # An out-of-order gossip packet from Node A arrives with wall_time = now (older than local state)
    stale_entity = CRDTEntityState(
        entity_id="TRK-RECON-1",
        owner_node="NODE-A",
        properties={"lat": 32.48, "lon": 34.79, "speed": 195.0},
        vector_clock=VectorClock({"NODE-A": 2}),
        wall_time=now,
    )
    delta_delayed = SyncDelta(
        sender_node_id="NODE-A",
        sequence_num=14,
        entities=[stale_entity],
        timestamp=now + 1.1,
    )
    delta_delayed.mac = delta_delayed.compute_mac(mesh_b.shared_secret)

    res = mesh_b.receive_delta(delta_delayed)
    assert res["accepted"] is True
    # Must NOT be quarantined as a Byzantine attack!
    assert res["quarantined_entities"] == 0
    assert len(mesh_b.rejected_updates) == 0
    # Newer local state must be preserved under LWW
    assert mesh_b.entities["TRK-RECON-1"].properties["lat"] == 32.5
    # Causal vector clock must be merged
    assert mesh_b.vector_clock.clock.get("NODE-A") == 2


def test_roe_fratricide_prevention_on_assumed_friend_and_ghost_track():
    """Verify ROE engine blocks fratricide against ASSUMED_FRIEND and denies engagement against ghost blips."""
    roe = RulesOfEngagementEngine()

    # 1. ASSUMED_FRIEND track: must be rejected under fratricide prevention
    track_assumed = MultiIntTrack(
        track_id="TRK-ALLIED-AIR-01",
        domain=WarfightingDomain.AIR,
        affiliation=Affiliation.ASSUMED_FRIEND,
        kinematics=KinematicState(lat=32.8, lon=35.5, altitude_m=4000.0),
        pid_confidence=0.95,
        anti_spoof_confidence=1.0,
    )
    plan_kinetic = type("MockPlan", (), {
        "effector_type": EffectorType.HARD_KINETIC_INTERCEPTOR,
        "effector_id": "EFF-MISSILE-01",
        "collateral_damage_risk": 0.02,
    })()

    ok_assumed, lease_assumed, reason_assumed = roe.verify_engagement(track_assumed, plan_kinetic)
    assert ok_assumed is False
    assert "fratricide protection" in reason_assumed.lower()
    assert lease_assumed is None

    # 2. Ghost track blip: must be rejected to prevent weapon wastage
    track_ghost = MultiIntTrack(
        track_id="TRK-CLUTTER-01",
        domain=WarfightingDomain.AIR,
        affiliation=Affiliation.HOSTILE,
        kinematics=KinematicState(lat=32.8, lon=35.5, altitude_m=4000.0),
        pid_confidence=0.90,
        anti_spoof_confidence=0.85,
        is_ghost_track=True,
    )
    ok_ghost, lease_ghost, reason_ghost = roe.verify_engagement(track_ghost, plan_kinetic)
    assert ok_ghost is False
    assert "ghost track" in reason_ghost.lower()
    assert lease_ghost is None


def test_effector_lease_signature_verification_and_tamper_detection():
    """Verify cryptographic HMAC signature verification on EffectorLease tokens."""
    roe = RulesOfEngagementEngine()

    track = MultiIntTrack(
        track_id="TRK-CONFIRMED-HOSTILE",
        domain=WarfightingDomain.AIR,
        affiliation=Affiliation.HOSTILE,
        kinematics=KinematicState(lat=33.1, lon=35.4, altitude_m=2000.0),
        pid_confidence=0.96,
        anti_spoof_confidence=0.99,
    )
    plan = type("MockPlan", (), {
        "effector_type": EffectorType.HARD_KINETIC_INTERCEPTOR,
        "effector_id": "EFF-KINETIC-09",
        "collateral_damage_risk": 0.04,
    })()

    ok, lease_id, _ = roe.verify_engagement(track, plan)
    assert ok is True
    lease = roe.issued_leases[lease_id]

    # Valid lease signature verifies successfully
    assert lease.verify_signature(roe.signing_secret) is True
    # Wrong secret fails verification
    assert lease.verify_signature(b"attacker-forged-secret") is False

    # Tampered target track ID fails verification
    tampered_lease = EffectorLease(
        lease_id=lease.lease_id,
        target_track_id="TRK-CIVILIAN-AIRLINER",
        effector_id=lease.effector_id,
        purpose=lease.purpose,
        issued_at=lease.issued_at,
        expires_at=lease.expires_at,
        policy_version=lease.policy_version,
        signature=lease.signature,
    )
    assert tampered_lease.verify_signature(roe.signing_secret) is False


def test_mesh_partition_lease_conflict_resolution():
    """Verify mesh partition healing resolves conflicting effector leases deterministically."""
    roe = RulesOfEngagementEngine()
    now = time.time()

    eff_single = EffectorAsset(
        effector_id="EFF-SOLO-LAUNCHER",
        name="Solo Kinetic Launcher",
        effector_type=EffectorType.HARD_KINETIC_INTERCEPTOR,
        domain=WarfightingDomain.AIR,
        lat=32.0,
        lon=34.8,
        inventory_count=1,
    )

    # Cluster A issued lease LSE-A at t = now (earlier timestamp)
    lease_a = roe._mint_lease("TRK-TARGET-1", "EFF-SOLO-LAUNCHER", "TACTICAL_ENGAGEMENT", issued_at=now, ttl_sec=60.0)
    roe.issued_leases[lease_a.lease_id] = lease_a

    # Cluster B issued conflicting lease LSE-B on the same effector at t = now + 5.0s
    lease_b = roe._mint_lease("TRK-TARGET-2", "EFF-SOLO-LAUNCHER", "TACTICAL_ENGAGEMENT", issued_at=now + 5.0, ttl_sec=60.0)

    # Sync remote lease B into Cluster A
    res_sync = roe.sync_remote_leases([lease_b], effectors=[eff_single])
    assert res_sync["conflicts_resolved"] == 1
    # Cluster A's earlier lease wins; Cluster B's conflicting lease is superseded
    assert roe.issued_leases[lease_a.lease_id].is_valid() is True
    assert roe.issued_leases[lease_b.lease_id].is_revoked is True
    assert "SUPERSEDED_BY_CONCURRENT_LEASE" in roe.issued_leases[lease_b.lease_id].revocation_reason

    # Forged lease rejection test
    forged_lease = EffectorLease(
        lease_id="LSE-FORGED",
        target_track_id="TRK-TARGET-3",
        effector_id="EFF-SOLO-LAUNCHER",
        purpose="TACTICAL_ENGAGEMENT",
        issued_at=now,
        expires_at=now + 60.0,
        policy_version="ROE-POL-2026.1",
        signature="BAD_SIG_123456",
    )
    res_forged = roe.sync_remote_leases([forged_lease], effectors=[eff_single])
    assert res_forged["rejected"] == 1
    assert "LSE-FORGED" not in roe.issued_leases


def test_predictive_wargame_defensive_screen_and_feint_deception():
    """Verify DEFENSIVE_SCREEN and FEINT_DECEPTION modify battlefield tactical geometries."""
    engine = PredictiveWargameEngine(simulation_depth=1, rollout_count=10, seed=42)

    # Test DEFENSIVE_SCREEN
    state_screen = BattlefieldState(
        blue_units=[UnitState("B1", "BLUE", lat=32.0, lon=34.8, health_pct=90.0, ammo_rounds=10),
                    UnitState("B2", "BLUE", lat=32.02, lon=34.82, health_pct=90.0, ammo_rounds=10)],
        red_units=[UnitState("R1", "RED", lat=32.2, lon=34.8, health_pct=90.0, ammo_rounds=8)],
    )
    engine._apply_action(state_screen, "BLUE", TacticalActionType.DEFENSIVE_SCREEN)
    # Defense posture boosts health
    assert state_screen.blue_units[0].health_pct > 90.0

    # Test FEINT_DECEPTION
    state_feint = BattlefieldState(
        blue_units=[UnitState("B1", "BLUE", lat=32.0, lon=34.8, health_pct=90.0, ammo_rounds=10),
                    UnitState("B2", "BLUE", lat=32.02, lon=34.82, health_pct=90.0, ammo_rounds=10)],
        red_units=[UnitState("R1", "RED", lat=32.2, lon=34.8, health_pct=90.0, ammo_rounds=8)],
    )
    r1_lat_before = state_feint.red_units[0].lat
    engine._apply_action(state_feint, "BLUE", TacticalActionType.FEINT_DECEPTION)
    # Red units misorient towards the feint
    assert state_feint.red_units[0].lat != r1_lat_before


def test_cockpit_api_defense_summary_endpoint(api_client):
    """Verify /api/cockpit/defense/summary endpoint returns complete aggregated metrics."""
    res = api_client.get("/api/cockpit/defense/summary")
    assert res.status_code == 200
    data = res.json()
    assert "total_tracks" in data
    assert "critical_threats" in data
    assert "active_plans" in data
    assert "effectors_ready" in data
    assert "roe_enforced" in data
    assert data["roe_enforced"] is True
    assert "active_leases" in data
    assert "gps_integrity" in data
    assert "emcon" in data
