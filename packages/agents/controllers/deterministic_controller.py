# Copyright (c) Ultrone Contributors. All rights reserved.
"""Deterministic Kinematic Waypoint Controller.

Translates high-level mission waypoints into rate-limited actuator setpoints
without relying on stochastic LLM generation for motor or flight dynamics.
"""

from __future__ import annotations

import math
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from .cbf_safety_filter import ControlBarrierSafetyFilter, SafetyFilterResult


@dataclass
class UnitKinematics:
    """State vector of an autonomous unit."""

    unit_id: str
    lat: float
    lon: float
    alt_m: float
    speed_mps: float = 0.0
    heading_deg: float = 0.0
    target_lat: Optional[float] = None
    target_lon: Optional[float] = None
    target_alt_m: Optional[float] = None
    target_speed_mps: float = 45.0
    active: bool = True
    last_update: float = field(default_factory=time.time)


class DeterministicWaypointController:
    """Hard-real-time deterministic controller executing waypoint navigation."""

    def __init__(
        self,
        safety_filter: Optional[ControlBarrierSafetyFilter] = None,
        max_acceleration_mps2: float = 5.0,
        max_climb_rate_mps: float = 15.0,
    ) -> None:
        self.safety_filter = safety_filter or ControlBarrierSafetyFilter()
        self.max_acceleration = max_acceleration_mps2
        self.max_climb_rate = max_climb_rate_mps
        self._units: Dict[str, UnitKinematics] = {}

    def register_unit(self, unit_id: str, lat: float, lon: float, alt_m: float) -> UnitKinematics:
        """Register an active asset."""
        unit = UnitKinematics(unit_id=unit_id, lat=lat, lon=lon, alt_m=alt_m)
        self._units[unit_id] = unit
        return unit

    def get_unit_state(self, unit_id: str) -> Optional[UnitKinematics]:
        return self._units.get(unit_id)

    def set_waypoint(
        self,
        unit_id: str,
        target_lat: float,
        target_lon: float,
        target_alt_m: float,
        speed_mps: float = 45.0,
    ) -> SafetyFilterResult:
        """Assign target waypoint, passing through CBF Safety Filter first."""
        unit = self._units.get(unit_id)
        if not unit:
            unit = self.register_unit(unit_id, target_lat, target_lon, target_alt_m)

        # Other unit positions for swarm collision avoidance
        other_positions: Dict[str, Tuple[float, float, float]] = {
            u_id: (u.lat, u.lon, u.alt_m)
            for u_id, u in self._units.items()
            if u_id != unit_id and u.active
        }

        # Pass through Control Barrier Safety Filter
        filter_res = self.safety_filter.filter_waypoint(
            current_pos=(unit.lat, unit.lon, unit.alt_m),
            proposed_target=(target_lat, target_lon, target_alt_m),
            proposed_speed_mps=speed_mps,
            other_units=other_positions,
        )

        unit.target_lat = filter_res.safe_lat
        unit.target_lon = filter_res.safe_lon
        unit.target_alt_m = filter_res.safe_alt_m
        unit.target_speed_mps = filter_res.safe_speed_mps
        return filter_res

    def step(self, dt: float = 1.0) -> Dict[str, Dict[str, Any]]:
        """Advance deterministic kinematic model by delta time dt (seconds)."""
        updates: Dict[str, Dict[str, Any]] = {}

        for unit_id, unit in self._units.items():
            if not unit.active or unit.target_lat is None or unit.target_lon is None:
                continue

            dist_m = ControlBarrierSafetyFilter._haversine_distance_m(
                unit.lat, unit.lon, unit.target_lat, unit.target_lon
            )

            # Reached waypoint
            if dist_m < 15.0 and abs(unit.alt_m - (unit.target_alt_m or unit.alt_m)) < 10.0:
                unit.speed_mps = 0.0
                updates[unit_id] = {
                    "status": "WAYPOINT_REACHED",
                    "lat": unit.lat,
                    "lon": unit.lon,
                    "alt_m": unit.alt_m,
                }
                continue

            # Speed rate limiting
            speed_err = unit.target_speed_mps - unit.speed_mps
            accel_step = max(-self.max_acceleration * dt, min(self.max_acceleration * dt, speed_err))
            unit.speed_mps = max(0.0, unit.speed_mps + accel_step)

            # Altitude rate limiting
            if unit.target_alt_m is not None:
                alt_err = unit.target_alt_m - unit.alt_m
                climb_step = max(-self.max_climb_rate * dt, min(self.max_climb_rate * dt, alt_err))
                unit.alt_m += climb_step

            # Horizontal displacement along bearing
            bearing = ControlBarrierSafetyFilter._bearing_rad(
                unit.lat, unit.lon, unit.target_lat, unit.target_lon
            )
            unit.heading_deg = math.degrees(bearing) % 360.0

            step_distance_m = min(dist_m, unit.speed_mps * dt)
            new_lat, new_lon = ControlBarrierSafetyFilter._project_point(
                unit.lat, unit.lon, step_distance_m, bearing
            )
            unit.lat = new_lat
            unit.lon = new_lon
            unit.last_update = time.time()

            updates[unit_id] = {
                "status": "NAVIGATING",
                "lat": unit.lat,
                "lon": unit.lon,
                "alt_m": unit.alt_m,
                "speed_mps": unit.speed_mps,
                "heading_deg": unit.heading_deg,
                "remaining_dist_m": dist_m - step_distance_m,
            }

        return updates
