# Copyright (c) Ultrone Contributors. All rights reserved.
"""PX4 / MAVLink Simulation-in-the-Loop (SITL) Dynamics Bridge.

Simulates 6-DOF kinematic state evolution with:
- Aerodynamic drag: F_drag = 0.5 * rho * v^2 * Cd * A
- Wind shear vectors (w_x, w_y, w_z) affecting ground track
- First-order actuator response lag: tau * du/dt + u = u_cmd
- Standard MAVLink telemetry framing (HEARTBEAT, GLOBAL_POSITION_INT, ATTITUDE)
"""

from __future__ import annotations

import math
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from .cbf_safety_filter import ControlBarrierSafetyFilter


@dataclass
class WindVector:
    """Atmospheric wind velocity vector."""

    vx_mps: float = 0.0  # Eastward wind
    vy_mps: float = 0.0  # Northward wind
    vz_mps: float = 0.0  # Vertical gust / downdraft


@dataclass
class MavlinkMessage:
    """Standardized MAVLink 2.0 message packet."""

    msg_id: str
    sys_id: int
    comp_id: int
    payload: Dict[str, Any]
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "msg_id": self.msg_id,
            "sys_id": self.sys_id,
            "comp_id": self.comp_id,
            "payload": self.payload,
            "timestamp": self.timestamp,
        }


@dataclass
class SITLVehicleState:
    """Physical telemetry state of simulated platform."""

    unit_id: str
    sys_id: int
    lat: float
    lon: float
    alt_m: float
    true_airspeed_mps: float = 0.0
    ground_speed_mps: float = 0.0
    heading_deg: float = 0.0
    roll_deg: float = 0.0
    pitch_deg: float = 0.0
    yaw_deg: float = 0.0
    target_speed_mps: float = 0.0
    target_lat: Optional[float] = None
    target_lon: Optional[float] = None
    target_alt_m: Optional[float] = None
    drag_coeff: float = 0.04
    cross_section_area_m2: float = 1.2
    mass_kg: float = 24.0
    air_density: float = 1.225  # kg/m^3 (sea level standard)
    actuator_lag_tau_s: float = 0.2  # 200ms first-order control delay
    battery_remaining_pct: float = 100.0


class PX4MavlinkSITLBridge:
    """SITL flight dynamics engine bridging actuator commands to simulated physics."""

    def __init__(
        self,
        wind: Optional[WindVector] = None,
        update_rate_hz: float = 50.0,
    ) -> None:
        self.wind = wind or WindVector()
        self.update_rate_hz = update_rate_hz
        self.dt = 1.0 / update_rate_hz
        self._vehicles: Dict[str, SITLVehicleState] = {}
        self._message_bus: List[MavlinkMessage] = []

    def spawn_vehicle(
        self,
        unit_id: str,
        sys_id: int,
        lat: float,
        lon: float,
        alt_m: float,
        initial_speed_mps: float = 0.0,
    ) -> SITLVehicleState:
        """Spawn a vehicle into the SITL environment."""
        state = SITLVehicleState(
            unit_id=unit_id,
            sys_id=sys_id,
            lat=lat,
            lon=lon,
            alt_m=alt_m,
            true_airspeed_mps=initial_speed_mps,
            ground_speed_mps=initial_speed_mps,
        )
        self._vehicles[unit_id] = state
        return state

    def send_mavlink_command(self, sys_id: int, command: str, params: Dict[str, Any]) -> MavlinkMessage:
        """Emulate sending a MAVLink command (e.g. MAV_CMD_DO_REPOSITION)."""
        vehicle = next((v for v in self._vehicles.values() if v.sys_id == sys_id), None)
        if not vehicle:
            return MavlinkMessage(
                msg_id="COMMAND_ACK",
                sys_id=sys_id,
                comp_id=1,
                payload={"command": command, "result": "MAV_RESULT_FAILED", "reason": "Unknown sys_id"},
            )

        if command == "SET_POSITION_TARGET_GLOBAL_INT":
            vehicle.target_lat = float(params.get("lat", vehicle.lat))
            vehicle.target_lon = float(params.get("lon", vehicle.lon))
            vehicle.target_alt_m = float(params.get("alt_m", vehicle.alt_m))
            vehicle.target_speed_mps = float(params.get("speed_mps", 45.0))
            result = "MAV_RESULT_ACCEPTED"
        else:
            result = "MAV_RESULT_UNSUPPORTED"

        ack = MavlinkMessage(
            msg_id="COMMAND_ACK",
            sys_id=sys_id,
            comp_id=1,
            payload={"command": command, "result": result},
        )
        self._message_bus.append(ack)
        return ack

    def step(self, dt: Optional[float] = None) -> List[MavlinkMessage]:
        """Step aerodynamic physics simulation forward by dt."""
        step_dt = dt or self.dt
        telemetry_msgs: List[MavlinkMessage] = []

        for unit_id, v in self._vehicles.items():
            if v.target_lat is None or v.target_lon is None:
                continue

            dist_to_target = ControlBarrierSafetyFilter._haversine_distance_m(
                v.lat, v.lon, v.target_lat, v.target_lon
            )

            # Reached waypoint
            if dist_to_target < 10.0 and abs(v.alt_m - (v.target_alt_m or v.alt_m)) < 5.0:
                v.target_speed_mps = 0.0

            # 1. First-Order Actuator Lag: tau * du/dt + u = u_cmd => du = (u_cmd - u) * (dt / tau)
            speed_error = v.target_speed_mps - v.true_airspeed_mps
            actuator_factor = min(1.0, step_dt / max(0.01, v.actuator_lag_tau_s))
            v.true_airspeed_mps += speed_error * actuator_factor

            # 2. Aerodynamic Drag: F_drag = 0.5 * rho * v^2 * Cd * A => decel = F_drag / mass
            f_drag = 0.5 * v.air_density * (v.true_airspeed_mps ** 2) * v.drag_coeff * v.cross_section_area_m2
            drag_decel = f_drag / v.mass_kg
            v.true_airspeed_mps = max(0.0, v.true_airspeed_mps - drag_decel * step_dt)

            # 3. Altitude climb/dive with rate limits
            if v.target_alt_m is not None:
                alt_diff = v.target_alt_m - v.alt_m
                max_climb = 15.0 * step_dt
                v.alt_m += max(-max_climb, min(max_climb, alt_diff))

            # 4. Heading and Ground Track with Wind Shear
            bearing = ControlBarrierSafetyFilter._bearing_rad(v.lat, v.lon, v.target_lat, v.target_lon)
            v.yaw_deg = math.degrees(bearing) % 360.0
            v.heading_deg = v.yaw_deg

            # Ground velocity vector = Airspeed vector + Wind vector
            vx_air = v.true_airspeed_mps * math.sin(bearing)
            vy_air = v.true_airspeed_mps * math.cos(bearing)

            vx_ground = vx_air + self.wind.vx_mps
            vy_ground = vy_air + self.wind.vy_mps
            v.ground_speed_mps = math.sqrt(vx_ground ** 2 + vy_ground ** 2)

            ground_bearing = math.atan2(vx_ground, vy_ground)
            displacement_m = v.ground_speed_mps * step_dt

            # Project new position
            new_lat, new_lon = ControlBarrierSafetyFilter._project_point(
                v.lat, v.lon, displacement_m, ground_bearing
            )
            v.lat = new_lat
            v.lon = new_lon

            # Deplete battery based on thrust output
            power_consumption = (v.true_airspeed_mps / 50.0) * 0.05 * step_dt
            v.battery_remaining_pct = max(0.0, v.battery_remaining_pct - power_consumption)

            # 5. Generate MAVLink Telemetry Packets
            pos_msg = MavlinkMessage(
                msg_id="GLOBAL_POSITION_INT",
                sys_id=v.sys_id,
                comp_id=1,
                payload={
                    "lat": int(v.lat * 1e7),
                    "lon": int(v.lon * 1e7),
                    "alt_mm": int(v.alt_m * 1e3),
                    "vx_cm_s": int(vx_ground * 100),
                    "vy_cm_s": int(vy_ground * 100),
                    "vz_cm_s": int(self.wind.vz_mps * 100),
                    "hdg_cdeg": int(v.heading_deg * 100),
                },
            )
            att_msg = MavlinkMessage(
                msg_id="ATTITUDE",
                sys_id=v.sys_id,
                comp_id=1,
                payload={
                    "roll": math.radians(v.roll_deg),
                    "pitch": math.radians(v.pitch_deg),
                    "yaw": math.radians(v.yaw_deg),
                },
            )
            telemetry_msgs.extend([pos_msg, att_msg])

        self._message_bus.extend(telemetry_msgs)
        return telemetry_msgs
