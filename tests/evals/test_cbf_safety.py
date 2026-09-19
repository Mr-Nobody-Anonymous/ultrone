# Copyright (c) Ultrone Contributors. All rights reserved.
import pytest

from packages.agents.controllers import (
    ControlBarrierSafetyFilter,
    DeterministicWaypointController,
    GeofenceZone,
)


def test_cbf_kinematic_bounds_enforcement():
    filter_ = ControlBarrierSafetyFilter(
        max_speed_mps=70.0,
        min_altitude_m=50.0,
        max_altitude_m=10000.0,
    )

    # Command exceeding speed and below altitude floor
    res = filter_.filter_waypoint(
        current_pos=(34.0, -118.0, 500.0),
        proposed_target=(34.1, -118.1, 20.0),  # below 50m
        proposed_speed_mps=120.0,  # above 70m/s
    )

    assert res.modified
    assert res.safe_speed_mps == 70.0
    assert res.safe_alt_m == 50.0
    assert len(res.violations) == 2


def test_cbf_geofence_exclusion_projection():
    filter_ = ControlBarrierSafetyFilter()
    # Add No-Fly Zone centered at (34.05, -118.25) with radius 1000m
    filter_.add_geofence(
        GeofenceZone(
            zone_id="NFZ-CIVILIAN-AIRPORT",
            center_lat=34.05,
            center_lon=-118.25,
            radius_m=1000.0,
            is_exclusion_zone=True,
        )
    )

    # Propose waypoint inside NFZ (dist ~ 0m)
    res = filter_.filter_waypoint(
        current_pos=(34.0, -118.25, 2000.0),
        proposed_target=(34.05, -118.25, 2000.0),
    )

    assert res.modified
    assert any("NFZ-CIVILIAN-AIRPORT" in v for v in res.violations)

    # Verify projected target is pushed OUTSIDE the NFZ radius
    dist_projected = ControlBarrierSafetyFilter._haversine_distance_m(
        res.safe_lat, res.safe_lon, 34.05, -118.25
    )
    assert dist_projected >= 1000.0


def test_cbf_swarm_minimum_separation_invariant():
    filter_ = ControlBarrierSafetyFilter(min_separation_m=50.0)

    # Propose target very close to another active unit
    other_pos = (34.0500, -118.2500, 2000.0)
    proposed = (34.0500, -118.2500, 2010.0)  # separation = 10m < 50m

    res = filter_.filter_waypoint(
        current_pos=(34.0400, -118.2500, 2000.0),
        proposed_target=proposed,
        other_units={"UAV-BETA-2": other_pos},
    )

    assert res.modified
    assert any("Collision hazard" in v for v in res.violations)
    # Target altitude was adjusted to guarantee >= 50m separation
    assert abs(res.safe_alt_m - other_pos[2]) >= 50.0


def test_deterministic_waypoint_controller_step_simulation():
    controller = DeterministicWaypointController()
    controller.register_unit("UAV-ALFA-1", lat=34.0, lon=-118.0, alt_m=1000.0)

    # Dispatch target
    res = controller.set_waypoint("UAV-ALFA-1", target_lat=34.01, target_lon=-118.0, target_alt_m=1100.0, speed_mps=50.0)
    assert res.safe

    # Step forward in time
    updates = controller.step(dt=2.0)
    assert "UAV-ALFA-1" in updates
    u1 = updates["UAV-ALFA-1"]
    assert u1["status"] == "NAVIGATING"
    assert u1["speed_mps"] > 0.0
    assert u1["lat"] > 34.0  # moved towards 34.01
