# Copyright (c) Ultrone Contributors. All rights reserved.
"""SensorMcpServer: MCP Server exposing Radar, Satellite SAR, and Telemetry feeds."""

from __future__ import annotations

import json
import math
import random
import time
from typing import Any, Dict, List, Optional

from .protocol import McpToolInputSchema
from .server import McpServer


from .streaming import McpTelemetryStreamer


class SensorMcpServer(McpServer):
    """Specialized MCP Server serving real-time and synthetic sensor streams."""

    def __init__(self, name: str = "ultrone-sensor-mcp", version: str = "1.0.0") -> None:
        super().__init__(name=name, version=version)
        self._tracks: Dict[str, Dict[str, Any]] = {}
        self.streamer = McpTelemetryStreamer()
        self._init_sensor_tools()
        self._init_sensor_resources()


    def _init_sensor_tools(self) -> None:
        # 1. Radar Sweep
        self.register_tool(
            name="radar_sweep",
            description="Performs an active radar sweep across a defined sector and returns tracked contacts.",
            input_schema=McpToolInputSchema(
                properties={
                    "sector_center_deg": {"type": "number", "description": "Center azimuth in degrees (0-360)"},
                    "beam_width_deg": {"type": "number", "description": "Azimuth beam width (default 30 deg)"},
                    "max_range_km": {"type": "number", "description": "Maximum detection range in km (default 150 km)"},
                },
                required=["sector_center_deg"],
            ),
            handler=self._handle_radar_sweep,
        )

        # 2. Satellite SAR Capture
        self.register_tool(
            name="satellite_sar_capture",
            description="Requests synthetic aperture radar (SAR) high-resolution imaging over coordinates.",
            input_schema=McpToolInputSchema(
                properties={
                    "target_lat": {"type": "number", "description": "Latitude (-90 to 90)"},
                    "target_lon": {"type": "number", "description": "Longitude (-180 to 180)"},
                    "resolution_m": {"type": "number", "description": "Desired resolution in meters (0.5 to 5.0)"},
                },
                required=["target_lat", "target_lon"],
            ),
            handler=self._handle_sar_capture,
        )

        # 3. Telemetry Spatial Query
        self.register_tool(
            name="query_telemetry",
            description="Queries live multi-domain telemetry feeds within a radius of given coordinates.",
            input_schema=McpToolInputSchema(
                properties={
                    "domain": {"type": "string", "description": "air, sea, land, space, or all"},
                    "center_lat": {"type": "number", "description": "Center latitude"},
                    "center_lon": {"type": "number", "description": "Center longitude"},
                    "radius_km": {"type": "number", "description": "Search radius in km"},
                },
                required=["center_lat", "center_lon", "radius_km"],
            ),
            handler=self._handle_query_telemetry,
        )

        # 4. EO/IR Track & Target Identification
        self.register_tool(
            name="eoir_track_target",
            description="Directs high-resolution Electro-Optical / Infrared gimbal to track target and estimate PID confidence.",
            input_schema=McpToolInputSchema(
                properties={
                    "target_id": {"type": "string", "description": "Target track ID"},
                    "spectral_mode": {"type": "string", "description": "visible, mwir, or lwir"},
                },
                required=["target_id"],
            ),
            handler=self._handle_eoir_track,
        )

    def _init_sensor_resources(self) -> None:
        self.register_resource(
            uri="sensor://radar/active_tracks",
            name="Active Radar Tracks",
            description="Dynamic JSON listing of currently established radar tracks",
            read_handler=lambda uri: json.dumps(list(self._tracks.values())),
        )

        self.register_resource(
            uri="sensor://system/health",
            name="Sensor Subsystem Health",
            description="Operational status of radar, SAR, and EO/IR pods",
            read_handler=lambda uri: json.dumps({
                "radar_active": True,
                "sar_constellation_available": True,
                "eoir_gimbal_ready": True,
                "timestamp": time.time(),
            }),
        )

    def _handle_radar_sweep(self, args: Dict[str, Any]) -> Dict[str, Any]:
        center = float(args.get("sector_center_deg", 0.0))
        max_range = float(args.get("max_range_km", 150.0))

        # Generate realistic contact
        track_id = f"TRK-{int(center):03d}-{random.randint(100, 999)}"
        contact = {
            "track_id": track_id,
            "azimuth_deg": center + random.uniform(-5.0, 5.0),
            "range_km": min(max_range, max(10.0, max_range * 0.45)),
            "altitude_m": 8500.0,
            "velocity_mps": 240.0,
            "rcs_m2": 2.5,
            "confidence": 0.88,
            "timestamp": time.time(),
        }
        self._tracks[track_id] = contact
        self.streamer.publish("telemetry/radar", contact)
        return {"sweep_complete": True, "contacts_found": 1, "tracks": [contact]}


    def _handle_sar_capture(self, args: Dict[str, Any]) -> Dict[str, Any]:
        lat = float(args.get("target_lat", 0.0))
        lon = float(args.get("target_lon", 0.0))
        res_m = float(args.get("resolution_m", 1.0))

        return {
            "capture_id": f"SAR-{int(time.time())}",
            "coordinates": {"lat": lat, "lon": lon},
            "resolution_m": res_m,
            "surface_roughness": 0.32,
            "anomalies_detected": [
                {"type": "metallic_cluster", "lat": lat + 0.001, "lon": lon + 0.001, "area_m2": 45.0}
            ],
            "cloud_penetration": 1.0,
            "timestamp": time.time(),
        }

    def _handle_query_telemetry(self, args: Dict[str, Any]) -> Dict[str, Any]:
        c_lat = float(args.get("center_lat", 0.0))
        c_lon = float(args.get("center_lon", 0.0))
        radius = float(args.get("radius_km", 50.0))
        domain = args.get("domain", "all")

        entities = [
            {
                "entity_id": f"UAV-ALFA-{i}",
                "domain": "air",
                "lat": c_lat + (i * 0.02),
                "lon": c_lon + (i * 0.02),
                "altitude_m": 3000.0,
                "battery_pct": 82 - (i * 4),
                "status": "PATROLLING",
            }
            for i in range(1, 4)
        ]
        return {"domain": domain, "search_radius_km": radius, "entity_count": len(entities), "entities": entities}

    def _handle_eoir_track(self, args: Dict[str, Any]) -> Dict[str, Any]:
        target_id = str(args.get("target_id", "TRK-001"))
        spectral = args.get("spectral_mode", "mwir")

        # Provide high-confidence PID result
        return {
            "target_id": target_id,
            "spectral_mode": spectral,
            "pid_score": 0.94,
            "classification": "MILITARY_VEHICLE",
            "thermal_signature_kw": 42.5,
            "estimated_speed_kmh": 65.0,
            "los_valid": True,
            "timestamp": time.time(),
        }
