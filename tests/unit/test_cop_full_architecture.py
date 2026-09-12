"""Comprehensive verification of the full ULTRONE Operational Architecture:
- Core Provenance (Lineage, Derivation, Audit)
- Geospatial Suite (Terrain, Imagery, 3D Tiles, Vector Tiles, Tracks, Spatial Index)
- Investigation & Case Management (Cases, Evidence, Timelines, Annotations, Reports)
- Workflows Engine (Actions, Approvals, Tasks, Audit)
- DARPA Scenario Simulation Engine
"""
import pytest
import time
from pathlib import Path

# 1. Core Provenance
from packages.core.provenance import (
    LineageNode,
    LineageGraph,
    DerivationStep,
    DerivationTrace,
    AuditRecord,
    AuditVerifier,
)

# 2. Geospatial Suite
from packages.geospatial import (
    LayerCategory,
    LayerDefinition,
    LayerRegistry,
    TerrainProvider,
    ElevationMesh,
    ImageryProvider,
    WMSClient,
    Tileset3D,
    Tile3DNode,
    BoundingVolume,
    VectorFeature,
    VectorTileLayer,
    MVTDecoder,
    Waypoint,
    TrackHistory,
    TrackManager,
    BoundingBox,
    SpatialIndex,
)

# 3. Investigation Suite
from packages.investigation import (
    Case,
    CaseManager,
    CaseStatus,
    ClassificationLevel,
    EvidenceItem,
    EvidenceType,
    EvidenceBoard,
    TimelineEvent,
    EventCorrelator,
    Hypothesis,
    Annotation,
    ReportGenerator,
)

# 4. Workflows Suite
from packages.workflows import (
    WorkflowAction,
    ActionRegistry,
    ApprovalStatus,
    ApprovalRequest,
    ApprovalGate,
    TaskStatus,
    WorkflowTask,
    TaskQueue,
    WorkflowAuditEntry,
    WorkflowAuditTrail,
)

# 5. DARPA Scenario Simulator
from apps.simulator.scenario_engine import (
    ScenarioDefinition,
    ScenarioEngine,
    ScenarioObjective,
    ScenarioStatus,
)


def test_core_provenance():
    # Lineage Graph
    graph = LineageGraph()
    sensor_node = graph.add_node(LineageNode(node_id="sensor_01", node_type="sensor", source_name="Radar-A"))
    fusion_node = graph.add_node(LineageNode(node_id="fusion_01", node_type="fusion_model", source_name="KalmanTracker"))
    inf_node = graph.add_node(LineageNode(node_id="inf_01", node_type="inference", source_name="Qwen-Tactical"))

    graph.add_edge("sensor_01", "fusion_01")
    graph.add_edge("fusion_01", "inf_01")

    trace = graph.trace_lineage("inf_01")
    assert len(trace) == 3
    assert any(n["node_id"] == "sensor_01" for n in trace)

    # Derivation Trace
    trace_obj = DerivationTrace(target_entity_id="ALPHA-1", attribute_name="classification")
    trace_obj.add_step(DerivationStep(step_id="s1", algorithm_or_model="YOLO-SAR", input_ids=["img_101"], output_id="box_01"))
    assert "YOLO-SAR" in trace_obj.summary()

    # Tamper-evident Audit Verifier
    verifier = AuditVerifier()
    verifier.append("rec_1", "ENTITY_CREATE", "operator_1", {"id": "ALPHA-1"})
    verifier.append("rec_2", "ENTITY_UPDATE", "operator_1", {"id": "ALPHA-1", "speed": 120})
    assert verifier.verify_integrity() is True


def test_geospatial_suite():
    # Terrain & Elevation
    provider = TerrainProvider()
    tile = provider.get_tile_mesh(z=10, x=5, y=5)
    assert tile.rows == 16
    elev = tile.get_elevation_at(30.55, 40.55)
    assert isinstance(elev, float)

    # Imagery
    img = ImageryProvider(name="OSM_Test")
    assert "tile.openstreetmap.org/10/5/5.png" in img.get_tile_url(10, 5, 5)

    # 3D Tiles
    root_node = Tile3DNode(geometric_error=100.0, bounding_volume=BoundingVolume("region", [0, 0, 10, 10]))
    tileset = Tileset3D(root=root_node)
    t_json = tileset.to_json()
    assert t_json["asset"]["version"] == "1.1"

    # Vector Tiles
    decoder = MVTDecoder()
    layers = decoder.decode(b"")
    assert len(layers) == 1
    assert layers[0].features[0].id == "contact_001"

    # Tracks & Kinematics
    tm = TrackManager()
    wp1 = Waypoint(lat=32.0, lon=34.0, speed_mps=100.0, heading_deg=90.0)
    th = tm.update_track("TARGET-1", wp1)
    future_pos = th.predict_future_position(delta_seconds=10.0)
    # Heading 90 is East, lon should increase
    assert future_pos[1] > 34.0

    # Spatial Index
    s_idx = SpatialIndex(cell_size_deg=0.5)
    s_idx.insert("E1", 32.1, 34.1, "alpha")
    s_idx.insert("E2", 35.0, 38.0, "far")
    results = s_idx.query_radius(32.1, 34.1, radius_km=20.0)
    assert len(results) == 1
    assert results[0][0] == "E1"


def test_investigation_suite():
    # Case Manager
    cm = CaseManager()
    case = cm.create_case("INV-99", "Suspicious Maritime Transit", "Commander Vance")
    case.pin_entity("CONTACT-42")
    assert "CONTACT-42" in case.pinned_entity_ids

    # Evidence Board
    board = EvidenceBoard(case_id="INV-99")
    item = EvidenceItem(
        evidence_id="EV-1",
        case_id="INV-99",
        evidence_type=EvidenceType.GEO_POLYGON,
        title="Restricted Zone Breach",
        description="Vessel crossed boundary 02",
        source_ref="AIS-Feed-1",
    )
    board.attach_evidence(item)
    assert len(board.get_items()) == 1
    assert len(item.sha256_hash) == 64

    # Timeline & Correlation
    correlator = EventCorrelator()
    ev = TimelineEvent(event_id="TEV-1", timestamp=time.time(), title="Radar Sighting", event_type="detection", entity_ids=["CONTACT-42"])
    correlator.add_event(ev)
    assert len(correlator.correlate_for_entity("CONTACT-42")) == 1

    # Hypothesis & Annotation
    hypo = Hypothesis(hypothesis_id="H1", case_id="INV-99", statement="Vessel is covertly rendezvousing")
    assert hypo.status == "open"
    ann = Annotation(annotation_id="A1", case_id="INV-99", author="Analyst-1", text="Confirm AIS disparity", target_type="entity")
    assert ann.author == "Analyst-1"

    # Report Generation
    dossier = ReportGenerator.generate_markdown(case, [item], findings_summary="Boundary violation confirmed.")
    assert "OPERATIONAL DOSSIER" in dossier
    assert "CONTACT-42" in dossier


def test_workflows_suite():
    # Action Registry
    registry = ActionRegistry()
    actions = registry.list_actions()
    assert len(actions) >= 6
    act = registry.get_action("dispatch_sensor")
    assert act is not None
    assert act.requires_approval is True

    # Approval Gate (HITL)
    gate = ApprovalGate()
    req = ApprovalRequest(
        request_id="REQ-01",
        action_id="dispatch_sensor",
        initiator_id="Qwen-2.5",
        target_entity_id="RADAR-04",
        rationale="Optimize sector coverage for target intercept",
    )
    gate.submit_request(req)
    assert len(gate.get_pending_requests()) == 1

    resolved = gate.resolve_request("REQ-01", approved=True, approver_id="Operator-Alpha")
    assert resolved.status == ApprovalStatus.APPROVED

    # Task Queue
    queue = TaskQueue()
    task = queue.dispatch("export_geotiff", {"resolution": 0.5})
    assert task.status == TaskStatus.QUEUED
    task.update_progress(50.0)
    assert task.status == TaskStatus.RUNNING
    task.complete({"file_size_bytes": 1048576})
    assert task.status == TaskStatus.COMPLETED

    # Workflow Audit Trail
    trail = WorkflowAuditTrail()
    trail.record("WLOG-1", "dispatch_sensor", "Operator-Alpha", "APPROVAL", {"status": "APPROVED"})
    trail.record("WLOG-2", "dispatch_sensor", "System", "EXECUTE", {"sensor_id": "RADAR-04"})
    assert trail.verify_chain() is True


def test_darpa_scenario_simulation():
    obj = ScenarioObjective(
        objective_id="OBJ-1",
        description="Maintain 90% tracking coverage over Area 51",
        target_metric="coverage_area_pct",
        threshold=90.0,
    )
    definition = ScenarioDefinition(
        scenario_id="SCEN-01",
        name="Swarm Intercept Scenario Alpha",
        description="DARPA testbed scenario for distributed situational awareness",
        entities=[{"id": "UAV-1", "speed_mps": 50.0, "heading_deg": 90.0}],
        objectives=[obj],
        timeline_duration_seconds=10.0,
    )
    engine = ScenarioEngine(definition)
    engine.initialize()
    assert engine.status == ScenarioStatus.RUNNING

    for _ in range(12):
        engine.step(1.0)

    assert engine.status == ScenarioStatus.COMPLETED
    scorecard = engine.evaluate()
    assert scorecard.objectives_achieved == 1
    assert scorecard.overall_score_pct == 100.0
    assert scorecard.decision_latency_avg_ms > 0
