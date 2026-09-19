# Copyright (c) Ultrone Contributors. All rights reserved.
"""F2T2EAPlanner: Strategic Cognitive Tier generating immutable TaskDAGs."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from .dag import DAGNode, NodeStatus, TaskDAG

logger = logging.getLogger("Ultrone.Harness.Planner")


@dataclass
class MissionDirective:
    """Strategic commander intent and operating boundaries."""

    mission_id: str
    target_description: str
    area_center_lat: float
    area_center_lon: float
    rules_of_engagement: List[str]
    no_strike_entities: List[Dict[str, Any]]
    min_pid_confidence: float = 0.85
    max_cde_radius_m: float = 150.0
    designated_asset_id: str = "UAV-ALFA-1"


class F2T2EAPlanner:
    """Strategic Planner Agent decomposing mission intent into an F2T2EA TaskDAG."""

    def __init__(self, model_name: str = "strategic-planner-v1") -> None:
        self.model_name = model_name

    def plan_mission(self, directive: MissionDirective) -> TaskDAG:
        """Compile a mission directive into an immutable F2T2EA Kill-Chain DAG."""
        dag = TaskDAG(name=f"f2t2ea-{directive.mission_id}")

        # 1. FIND Stage: Search sector using Radar or Telemetry
        node_find = DAGNode(
            node_id="stage-1-find",
            phase="FIND",
            description=f"Sweep area sector around ({directive.area_center_lat}, {directive.area_center_lon})",
            tool_name="radar_sweep",
            parameters={
                "sector_center_deg": 90.0,
                "beam_width_deg": 45.0,
                "max_range_km": 100.0,
            },
            prerequisites=[],
            acceptance_criteria=["sweep_complete", "contacts_found"],
            constraints=["Sector beam within operational envelope"],
        )
        dag.add_node(node_find)

        # 2. FIX Stage: High-resolution SAR imaging to pin target coordinate
        node_fix = DAGNode(
            node_id="stage-2-fix",
            phase="FIX",
            description="Acquire synthetic aperture radar (SAR) capture to confirm coordinates",
            tool_name="satellite_sar_capture",
            parameters={
                "target_lat": directive.area_center_lat,
                "target_lon": directive.area_center_lon,
                "resolution_m": 1.0,
            },
            prerequisites=["stage-1-find"],
            acceptance_criteria=["capture_id", "coordinates"],
            constraints=["Zero sensor blackout"],
        )
        dag.add_node(node_fix)

        # 3. TRACK Stage: EO/IR Gimbal lock & Positive Identification (PID)
        node_track = DAGNode(
            node_id="stage-3-track",
            phase="TRACK",
            description="Acquire persistent EO/IR track and compute PID confidence",
            tool_name="eoir_track_target",
            parameters={
                "target_id": "TRK-001",
                "spectral_mode": "mwir",
            },
            prerequisites=["stage-2-fix"],
            acceptance_criteria=["pid_score", "classification"],
            constraints=[f"PID confidence >= {directive.min_pid_confidence:.2f}"],
        )
        dag.add_node(node_track)

        # 4. TARGET Stage: Waypoint positioning & weapon solution
        node_target = DAGNode(
            node_id="stage-4-target",
            phase="TARGET",
            description="Position asset into firing basket and verify CDE",
            tool_name="dispatch_waypoint",
            parameters={
                "unit_id": directive.designated_asset_id,
                "lat": directive.area_center_lat,
                "lon": directive.area_center_lon,
                "alt_m": 3000.0,
                "speed_mps": 55.0,
            },
            prerequisites=["stage-3-track"],
            acceptance_criteria=["status", "WAYPOINT_ACCEPTED"],
            constraints=[
                "Zero penetration of prohibited No-Fly Zones",
                f"Collateral damage estimate radius <= {directive.max_cde_radius_m:.0f}m",
            ],
        )
        dag.add_node(node_target)

        # 5. ENGAGE Stage: Kinetic / Electronic weapon authorization
        node_engage = DAGNode(
            node_id="stage-5-engage",
            phase="ENGAGE",
            description="Execute authorized engagement with verified ROE clearance token",
            tool_name="designate_target",
            parameters={
                "unit_id": directive.designated_asset_id,
                "target_id": "TRK-001",
                "weapon_mode": "laser_guided",
                "roe_clearance_token": "PENDING_GRADER_EVALUATION",
            },
            prerequisites=["stage-4-target"],
            acceptance_criteria=["TARGET_ENGAGED", "clearance"],
            constraints=[
                "Valid ROE clearance token required",
                "No strike on coordinates matching No-Strike List",
            ],
        )
        dag.add_node(node_engage)

        # 6. ASSESS Stage: Battle Damage Assessment (BDA)
        node_assess = DAGNode(
            node_id="stage-6-assess",
            phase="ASSESS",
            description="Perform post-strike BDA imagery capture",
            tool_name="satellite_sar_capture",
            parameters={
                "target_lat": directive.area_center_lat,
                "target_lon": directive.area_center_lon,
                "resolution_m": 0.5,
            },
            prerequisites=["stage-5-engage"],
            acceptance_criteria=["capture_id", "anomalies_detected"],
            constraints=["Assess target neutralization"],
        )
        dag.add_node(node_assess)

        logger.info(
            "F2T2EAPlanner compiled 6-stage TaskDAG for mission '%s'", directive.mission_id
        )
        return dag
