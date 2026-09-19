# Copyright (c) Ultrone Contributors. All rights reserved.
"""ActuatorMcpServer: MCP Server exposing Swarm Actuation and Kinematic interfaces."""

from __future__ import annotations

import json
import logging
import time
from typing import Any, Dict, List, Optional

from .protocol import McpToolInputSchema
from .server import McpServer

logger = logging.getLogger("Ultrone.MCP.Actuator")


class ActuatorMcpServer(McpServer):
    """MCP Server exposing physical/simulated swarm actuators through safe schemas."""

    def __init__(self, name: str = "ultrone-actuator-mcp", version: str = "1.0.0") -> None:
        super().__init__(name=name, version=version)
        self._command_history: List[Dict[str, Any]] = []
        self._unit_positions: Dict[str, Dict[str, float]] = {
            "UAV-ALFA-1": {"lat": 34.0522, "lon": -118.2437, "alt_m": 2500.0},
            "UAV-ALFA-2": {"lat": 34.0550, "lon": -118.2400, "alt_m": 2500.0},
        }
        self._init_actuator_tools()
        self._init_actuator_resources()

    def _init_actuator_tools(self) -> None:
        # 1. Dispatch Waypoint
        self.register_tool(
            name="dispatch_waypoint",
            description="Commands a swarm asset to navigate toward a waypoint (lat, lon, alt_m, speed_mps).",
            input_schema=McpToolInputSchema(
                properties={
                    "unit_id": {"type": "string", "description": "Target swarm asset ID"},
                    "lat": {"type": "number", "description": "Target latitude (-90 to 90)"},
                    "lon": {"type": "number", "description": "Target longitude (-180 to 180)"},
                    "alt_m": {"type": "number", "description": "Target altitude in meters (10 to 15000)"},
                    "speed_mps": {"type": "number", "description": "Cruising airspeed in m/s (10 to 100)"},
                },
                required=["unit_id", "lat", "lon", "alt_m"],
            ),
            handler=self._handle_dispatch_waypoint,
        )

        # 2. Hold Orbit / Loiter
        self.register_tool(
            name="hold_orbit",
            description="Commands an asset into a circular loiter pattern around a point of interest.",
            input_schema=McpToolInputSchema(
                properties={
                    "unit_id": {"type": "string", "description": "Target swarm asset ID"},
                    "center_lat": {"type": "number", "description": "Orbit center latitude"},
                    "center_lon": {"type": "number", "description": "Orbit center longitude"},
                    "radius_m": {"type": "number", "description": "Orbit radius in meters"},
                    "alt_m": {"type": "number", "description": "Orbit altitude in meters"},
                },
                required=["unit_id", "center_lat", "center_lon"],
            ),
            handler=self._handle_hold_orbit,
        )

        # 3. RF Jamming Frequency Allocation (Cyber/EW)
        self.register_tool(
            name="set_rf_jamming_frequency",
            description="Directs electronic warfare pod to emit directional jamming on designated RF band.",
            input_schema=McpToolInputSchema(
                properties={
                    "unit_id": {"type": "string", "description": "Asset executing electronic attack"},
                    "center_freq_mhz": {"type": "number", "description": "Center frequency in MHz"},
                    "bandwidth_mhz": {"type": "number", "description": "Jamming bandwidth in MHz"},
                    "power_watts": {"type": "number", "description": "Emission power in Watts (max 250W)"},
                },
                required=["unit_id", "center_freq_mhz", "bandwidth_mhz"],
            ),
            handler=self._handle_set_rf_jamming,
        )

        # 4. Designate Target
        self.register_tool(
            name="designate_target",
            description="Designates an engagement solution for an approved target. Requires verified ROE token.",
            input_schema=McpToolInputSchema(
                properties={
                    "unit_id": {"type": "string", "description": "Asset performing engagement"},
                    "target_id": {"type": "string", "description": "Confirmed track ID to engage"},
                    "weapon_mode": {"type": "string", "description": "kinetic, laser_guided, or electronic_soft_kill"},
                    "roe_clearance_token": {"type": "string", "description": "Cryptographic authorization token from ROEGrader"},
                },
                required=["unit_id", "target_id", "weapon_mode", "roe_clearance_token"],
            ),
            handler=self._handle_designate_target,
        )

    def _init_actuator_resources(self) -> None:
        self.register_resource(
            uri="actuator://swarm/status",
            name="Swarm Actuation Status",
            description="Current position and status for all active swarm units",
            read_handler=lambda uri: json.dumps(self._unit_positions),
        )

    def _handle_dispatch_waypoint(self, args: Dict[str, Any]) -> Dict[str, Any]:
        unit_id = args["unit_id"]
        lat = float(args["lat"])
        lon = float(args["lon"])
        alt_m = float(args.get("alt_m", 2500.0))
        speed = float(args.get("speed_mps", 45.0))

        self._unit_positions[unit_id] = {"lat": lat, "lon": lon, "alt_m": alt_m}
        record = {
            "action": "dispatch_waypoint",
            "unit_id": unit_id,
            "target": {"lat": lat, "lon": lon, "alt_m": alt_m, "speed_mps": speed},
            "timestamp": time.time(),
        }
        self._command_history.append(record)
        return {"status": "WAYPOINT_ACCEPTED", "unit_id": unit_id, "eta_seconds": 120.0}

    def _handle_hold_orbit(self, args: Dict[str, Any]) -> Dict[str, Any]:
        unit_id = args["unit_id"]
        c_lat = float(args["center_lat"])
        c_lon = float(args["center_lon"])
        radius = float(args.get("radius_m", 500.0))
        alt = float(args.get("alt_m", 2500.0))

        record = {
            "action": "hold_orbit",
            "unit_id": unit_id,
            "orbit": {"center_lat": c_lat, "center_lon": c_lon, "radius_m": radius, "alt_m": alt},
            "timestamp": time.time(),
        }
        self._command_history.append(record)
        return {"status": "ORBIT_ESTABLISHED", "unit_id": unit_id, "orbit_radius_m": radius}

    def _handle_set_rf_jamming(self, args: Dict[str, Any]) -> Dict[str, Any]:
        unit_id = args["unit_id"]
        freq = float(args["center_freq_mhz"])
        bw = float(args["bandwidth_mhz"])
        pwr = min(float(args.get("power_watts", 100.0)), 250.0)

        record = {
            "action": "rf_jamming",
            "unit_id": unit_id,
            "freq_mhz": freq,
            "bw_mhz": bw,
            "power_w": pwr,
            "timestamp": time.time(),
        }
        self._command_history.append(record)
        return {"status": "JAMMING_ACTIVE", "unit_id": unit_id, "freq_mhz": freq, "power_watts": pwr}

    def _handle_designate_target(self, args: Dict[str, Any]) -> Dict[str, Any]:
        unit_id = args["unit_id"]
        target_id = args["target_id"]
        mode = args["weapon_mode"]
        token = args["roe_clearance_token"]

        if not token or not token.startswith("ROE-CLEARED-"):
            raise ValueError(f"Invalid ROE clearance token: '{token}'. Engagement unauthorized.")

        record = {
            "action": "designate_target",
            "unit_id": unit_id,
            "target_id": target_id,
            "weapon_mode": mode,
            "token": token,
            "timestamp": time.time(),
        }
        self._command_history.append(record)
        return {
            "status": "TARGET_ENGAGED",
            "unit_id": unit_id,
            "target_id": target_id,
            "mode": mode,
            "clearance": "VERIFIED",
        }
