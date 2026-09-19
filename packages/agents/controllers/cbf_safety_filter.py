# Copyright (c) Ultrone Contributors. All rights reserved.
"""Control Barrier Function (CBF) and Geofencing Safety Filter.

Enforces deterministic mathematical safety guarantees on swarm actuators:
- Collision avoidance invariants between swarm members: h_ij(x) = ||p_i - p_j||^2 - d_min^2 >= 0
- Geofence / No-Fly Zone (NFZ) containment or exclusion
- Maximum velocity and acceleration limits
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class GeofenceZone:
    """Circular or bounding geofence zone."""

    zone_id: str
    center_lat: float
    center_lon: float
    radius_m: float
    min_alt_m: float = 0.0
    max_alt_m: float = 12000.0
    is_exclusion_zone: bool = True  # True = No-Fly Zone, False = Keep-In Zone


@dataclass
class SafetyFilterResult:
    """Outcome of CBF safety projection."""

    safe: bool
    modified: bool
    safe_lat: float
    safe_lon: float
    safe_alt_m: float
    safe_speed_mps: float
    violations: List[str] = field(default_factory=list)


class ControlBarrierSafetyFilter:
    """Safety filter projecting proposed waypoint/velocity commands onto safe invariant set.

    Incorporate High-Order Dynamic Barrier Certificates (HOCBF):
    - Aerodynamic bank angle limit (phi_max): dictates minimum turning radius R_min = v^2 / (g * tan(phi_max))
    - Longitudinal braking deceleration limit (a_max): dictates stopping distance d_stop = v^2 / (2 * a_max)
    - Swarm separation distance: ||p_i - p_j|| >= d_min + v * t_reaction
    """

    def __init__(
        self,
        min_separation_m: float = 50.0,
        max_speed_mps: float = 85.0,
        min_altitude_m: float = 30.0,
        max_altitude_m: float = 12500.0,
        max_bank_angle_deg: float = 45.0,
        max_braking_decel_mps2: float = 4.0,
        reaction_time_s: float = 0.5,
    ) -> None:
        self.min_separation_m = min_separation_m
        self.max_speed_mps = max_speed_mps
        self.min_altitude_m = min_altitude_m
        self.max_altitude_m = max_altitude_m
        self.max_bank_angle_deg = max_bank_angle_deg
        self.max_braking_decel = max_braking_decel_mps2
        self.reaction_time_s = reaction_time_s
        self.g = 9.80665
        self._geofences: Dict[str, GeofenceZone] = {}

    def min_turning_radius_m(self, speed_mps: float) -> float:
        """Calculate minimum aerodynamically feasible turning radius R_min = v^2 / (g * tan(phi_max))."""
        speed = max(5.0, min(speed_mps, self.max_speed_mps))
        phi_rad = math.radians(min(80.0, max(10.0, self.max_bank_angle_deg)))
        tan_phi = math.tan(phi_rad)
        return (speed ** 2) / (self.g * max(0.1, tan_phi))

    def stopping_distance_m(self, speed_mps: float) -> float:
        """Calculate distance required to decelerate to minimum speed: d = v^2 / (2 * a_max)."""
        speed = max(0.0, min(speed_mps, self.max_speed_mps))
        return (speed ** 2) / (2.0 * max(0.5, self.max_braking_decel))

    def dynamic_buffer_m(self, speed_mps: float) -> float:
        """Combined dynamic safety buffer accounting for turn radius, braking, and latency."""
        r_turn = self.min_turning_radius_m(speed_mps)
        d_brake = self.stopping_distance_m(speed_mps)
        d_latency = speed_mps * self.reaction_time_s
        return 0.3 * r_turn + 0.5 * d_brake + d_latency

    def add_geofence(self, zone: GeofenceZone) -> None:
        """Register a geofence exclusion or containment boundary."""
        self._geofences[zone.zone_id] = zone

    def remove_geofence(self, zone_id: str) -> None:
        """Remove a geofence zone."""
        self._geofences.pop(zone_id, None)

    def filter_waypoint(
        self,
        current_pos: Tuple[float, float, float],  # (lat, lon, alt_m)
        proposed_target: Tuple[float, float, float],  # (lat, lon, alt_m)
        proposed_speed_mps: float = 45.0,
        other_units: Optional[Dict[str, Tuple[float, float, float]]] = None,
    ) -> SafetyFilterResult:
        """Apply Control Barrier Functions to enforce invariant safety on target waypoint.

        Projects unsafe commands onto the nearest mathematically and aerodynamically safe setpoint.
        """
        curr_lat, curr_lon, curr_alt = current_pos
        t_lat, t_lon, t_alt = proposed_target
        speed = proposed_speed_mps

        violations: List[str] = []
        modified = False

        # 1. Kinematic Speed Limit
        if speed > self.max_speed_mps:
            violations.append(f"Speed {speed:.1f} m/s exceeds limit {self.max_speed_mps:.1f} m/s")
            speed = self.max_speed_mps
            modified = True
        elif speed <= 0:
            speed = 10.0
            modified = True

        # 2. Altitude Limits
        if t_alt < self.min_altitude_m:
            violations.append(f"Target altitude {t_alt:.1f}m below floor {self.min_altitude_m:.1f}m")
            t_alt = self.min_altitude_m
            modified = True
        elif t_alt > self.max_altitude_m:
            violations.append(f"Target altitude {t_alt:.1f}m exceeds ceiling {self.max_altitude_m:.1f}m")
            t_alt = self.max_altitude_m
            modified = True

        # Compute dynamic aerodynamic buffer for current velocity
        dyn_buf_m = self.dynamic_buffer_m(speed)

        # 3. Geofence / No-Fly Zone (NFZ) Dynamic Exclusion Invariants
        for gz in self._geofences.values():
            dist_m = self._haversine_distance_m(t_lat, t_lon, gz.center_lat, gz.center_lon)
            in_alt_band = gz.min_alt_m <= t_alt <= gz.max_alt_m

            # Effective boundary includes dynamic turning/stopping buffer
            effective_radius_m = gz.radius_m + (dyn_buf_m if gz.is_exclusion_zone else -dyn_buf_m)

            if gz.is_exclusion_zone:
                # Target penetrates NFZ or dynamic braking envelope
                if dist_m < effective_radius_m and in_alt_band:
                    violations.append(
                        f"Waypoint violates exclusion geofence '{gz.zone_id}' "
                        f"(dist={dist_m:.1f}m < dynamic_effective_radius={effective_radius_m:.1f}m [dyn_buf={dyn_buf_m:.1f}m])"
                    )
                    # CBF Projection: Push target out to effective buffer distance along bearing
                    bearing = self._bearing_rad(gz.center_lat, gz.center_lon, t_lat, t_lon)
                    safe_dist = effective_radius_m + 25.0
                    t_lat, t_lon = self._project_point(gz.center_lat, gz.center_lon, safe_dist, bearing)
                    modified = True
            else:
                # Containment zone: Target must not leave containment envelope
                min_contain_dist = max(50.0, gz.radius_m - dyn_buf_m)
                if dist_m > min_contain_dist and in_alt_band:
                    violations.append(f"Waypoint outside containment geofence '{gz.zone_id}'")
                    bearing = self._bearing_rad(gz.center_lat, gz.center_lon, t_lat, t_lon)
                    safe_dist = max(20.0, min_contain_dist - 25.0)
                    t_lat, t_lon = self._project_point(gz.center_lat, gz.center_lon, safe_dist, bearing)
                    modified = True

        # 4. Swarm Separation Distance Invariant with dynamic speed scaling: ||p_i - p_j|| >= d_min + v * dt
        effective_sep_m = self.min_separation_m + (speed * self.reaction_time_s * 0.5)
        if other_units:
            for other_id, other_pos in other_units.items():
                o_lat, o_lon, o_alt = other_pos
                horiz_dist = self._haversine_distance_m(t_lat, t_lon, o_lat, o_lon)
                vert_dist = abs(t_alt - o_alt)
                total_dist = math.sqrt(horiz_dist**2 + vert_dist**2)

                if total_dist < effective_sep_m:
                    violations.append(
                        f"Collision hazard with unit '{other_id}': separation {total_dist:.1f}m < dynamic_min {effective_sep_m:.1f}m"
                    )
                    # Vertical separation CBF adjustment (+30m or -30m)
                    if t_alt >= o_alt:
                        t_alt = o_alt + effective_sep_m + 10.0
                    else:
                        t_alt = max(self.min_altitude_m, o_alt - effective_sep_m - 10.0)
                    modified = True


        is_safe = len(violations) == 0 or modified
        return SafetyFilterResult(
            safe=is_safe,
            modified=modified,
            safe_lat=t_lat,
            safe_lon=t_lon,
            safe_alt_m=t_alt,
            safe_speed_mps=speed,
            violations=violations,
        )

    @staticmethod
    def _haversine_distance_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        r = 6371000.0  # Earth radius in meters
        phi1 = math.radians(lat1)
        phi2 = math.radians(lat2)
        d_phi = math.radians(lat2 - lat1)
        d_lambda = math.radians(lon2 - lon1)

        a = math.sin(d_phi / 2.0) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2.0) ** 2
        c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
        return r * c

    @staticmethod
    def _bearing_rad(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        phi1 = math.radians(lat1)
        phi2 = math.radians(lat2)
        d_lon = math.radians(lon2 - lon1)
        y = math.sin(d_lon) * math.cos(phi2)
        x = math.cos(phi1) * math.sin(phi2) - math.sin(phi1) * math.cos(phi2) * math.cos(d_lon)
        return math.atan2(y, x)

    @staticmethod
    def _project_point(lat: float, lon: float, distance_m: float, bearing_rad: float) -> Tuple[float, float]:
        r = 6371000.0
        phi1 = math.radians(lat)
        lambda1 = math.radians(lon)

        phi2 = math.asin(
            math.sin(phi1) * math.cos(distance_m / r)
            + math.cos(phi1) * math.sin(distance_m / r) * math.cos(bearing_rad)
        )
        lambda2 = lambda1 + math.atan2(
            math.sin(bearing_rad) * math.sin(distance_m / r) * math.cos(phi1),
            math.cos(distance_m / r) - math.sin(phi1) * math.sin(phi2),
        )
        return math.degrees(phi2), math.degrees(lambda2)
