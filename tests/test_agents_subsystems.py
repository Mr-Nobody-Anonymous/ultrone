# Copyright (c) Ultrone Contributors. All rights reserved.
"""Tests for the hierarchical capability model, structured command
system, and subsystem-composed platforms."""

import pytest

from agents.capabilities import (
    HierarchicalCapabilitySet,
    combine,
    validate_leaves,
)
from agents.commands import Command, CommandBus
from agents.subsystems.platform_subsystems import (
    AutonomySubsystem,
    HealthSubsystem,
    NavigationSubsystem,
    PayloadSubsystem,
    PowerSubsystem,
    PropulsionSubsystem,
    SensorSubsystem,
)


class TestHierarchicalCapabilities:
    def test_unknown_leaf_rejected(self):
        with pytest.raises(ValueError):
            validate_leaves(["warp_drive"])

    def test_available_returns_pruned_tree(self):
        caps = HierarchicalCapabilitySet(
            ["translation", "rotation", "visual", "transmit"])
        assert caps.available() == {
            "mobility": ["translation", "rotation"],
            "sensing": ["visual"],
            "communication": ["transmit"]}

    def test_covers_and_branch_queries(self):
        caps = HierarchicalCapabilitySet(
            ["navigation", "observation", "storage"])
        assert caps.covers({"navigation", "observation"})
        assert not caps.covers({"navigation", "repair"})
        assert caps.branch("power") == {"storage"}
        assert len(caps) == 3

    def test_combine_teams(self):
        a = HierarchicalCapabilitySet(["translation"])
        b = HierarchicalCapabilitySet(["visual"])
        assert combine(a, b).covers({"translation", "visual"})


class TestCommandBus:
    def test_unknown_subsystem_fails_cleanly(self):
        bus = CommandBus()
        result = bus.execute(Command("warp", "engage", {}))
        assert not result.success
        assert "unknown subsystem" in result.reason

    def test_subsystem_registration_duplicate_rejected(self):
        bus = CommandBus()
        bus.register(PowerSubsystem())
        with pytest.raises(ValueError):
            bus.register(PowerSubsystem())


class TestPropulsion:
    def test_throttle_requires_running_engine(self):
        prop = PropulsionSubsystem()
        bus = CommandBus()
        bus.register(prop)
        r = bus.execute(Command("propulsion", "set_throttle",
                                {"value": 0.5}))
        assert not r.success
        assert "engine off" in r.reason

    def test_fuel_burns_and_engine_auto_stops(self):
        prop = PropulsionSubsystem(fuel_capacity=1.0)
        bus = CommandBus()
        bus.register(prop)
        bus.execute(Command("propulsion", "start_engine"))
        bus.execute(Command("propulsion", "set_throttle", {"value": 1.0}))
        for t in range(5):
            prop.tick(t)
        assert prop.fuel == 0.0
        assert prop.engine_on is False
        assert any("fuel exhausted" in f["reason"] for f in prop.faults)

    def test_refuel_restores(self):
        prop = PropulsionSubsystem()
        prop.fuel = 20.0
        assert prop.handle("refuel", {}) == prop.fuel_capacity


class TestPowerNavigationSensors:
    def test_power_drain_then_recharge(self):
        power = PowerSubsystem(battery_pct=50.0, generation_kw=1.0)
        power.set_load(3.0)
        power.tick(1)
        assert power.battery_pct < 50.0
        power.recharge(pct=60)
        assert power.battery_pct == pytest.approx(100.0)

    def test_navigation_destination_tracking(self):
        nav = NavigationSubsystem(x=0.0, y=0.0)
        nav.handle("set_destination", {"position": [3.0, 4.0]})
        assert nav.distance_to_destination() == pytest.approx(5.0)

    def test_sensor_mode_whitelist(self):
        sensors = SensorSubsystem(seed=1)
        with pytest.raises(RuntimeError):
            sensors.handle("set_mode", {"mode": "x_ray"})
        scan = sensors.handle("scan", {"targets": 2})
        assert set(scan["readings"]) == {"contact_0", "contact_1"}


class TestPayloadHealthAutonomy:
    def test_payload_capacity_enforced(self):
        payload = PayloadSubsystem(capacity_kg=100.0)
        with pytest.raises(RuntimeError):
            payload.handle("load", {"kg": 150.0})
        payload.handle("load", {"kg": 40.0})
        assert payload.carried_kg == 40.0

    def test_health_diagnostics_and_repair(self):
        health = HealthSubsystem(wear_rate=30.0)
        for _ in range(3):
            health.tick(1)
        report = health.handle("run_diagnostics")
        assert report["service_due"] is True
        health.handle("repair")
        assert health.wear == 0.0

    def test_autonomy_task_queue(self):
        auto = AutonomySubsystem()
        assert auto.handle("enqueue_task", {"task": {"go": True}}) == 1
        assert auto.handle("pop_task") == {"go": True}
        assert auto.handle("pop_task") is None


class TestSubsystemComposedPlatforms:
    def test_survey_aircraft_full_mission(self):
        from agents.civilian import SurveyAircraftAgent

        agent = SurveyAircraftAgent("survey-1", seed=0)
        result = agent.execute_mission({
            "type": "survey_flight",
            "waypoints": [[8, 6], [14, 12], [6, 14]],
        })
        assert result["success"], result
        assert result["waypoints_scanned"] == 3
        assert agent.propulsion.fuel < agent.propulsion.fuel_capacity
        # Every operation went through the structured command interface.
        assert set(agent.bus.names()) >= {
            "propulsion", "navigation", "sensors", "power", "health"}

    def test_delivery_truck_round_trip(self):
        from agents.civilian import DeliveryTruckAgent

        agent = DeliveryTruckAgent("truck-1")
        result = agent.execute_mission({
            "type": "delivery", "destination": [18.0, 14.0],
            "cargo_kg": 120.0,
        })
        assert result["success"], result
        assert result["delivered_kg"] == 120.0
        assert result["battery_pct"] < 90.0      # electric drive drained

    def test_overload_refused_before_departure(self):
        from agents.civilian import DeliveryTruckAgent

        agent = DeliveryTruckAgent("truck-2")
        result = agent.execute_mission({
            "type": "delivery", "destination": [5, 5], "cargo_kg": 900.0,
        })
        assert not result["success"]
        assert "capacity" in (result.get("reason") or "")

    def test_registered_in_civilian_registry(self):
        from agents.registry import list_agent_types
        from data.entities import DomainType

        types = list_agent_types(DomainType.GENERAL)
        assert {"survey_aircraft", "delivery_truck"} <= set(types)