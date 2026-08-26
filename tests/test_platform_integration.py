# Copyright (c) Ultrone Contributors. All rights reserved.
"""Tests: UCL->CommandBus unification, new subsystems, fault injection,
unified PlatformState, and the simulation safety boundary."""

import pytest

from agents.commands import Command, CommandBus
from agents.platform_control import (
    SubsystemPlatformController,
    build_platform_state,
)
from agents.subsystems.faults import FaultInjector
from agents.subsystems.platform_subsystems import (
    AttitudeSubsystem,
    AutonomySubsystem,
    CommunicationSubsystem,
    EnvironmentSubsystem,
    HealthSubsystem,
    NavigationSubsystem,
    PayloadSubsystem,
    PowerSubsystem,
    PropulsionSubsystem,
    ResourceSubsystem,
    SensorSubsystem,
    ThermalSubsystem,
)


def _full_bus():
    bus = CommandBus()
    for sub in (PropulsionSubsystem(fuel_capacity=50.0),
                PowerSubsystem(battery_pct=90.0),
                NavigationSubsystem(x=2.0, y=2.0),
                SensorSubsystem(seed=0),
                CommunicationSubsystem(),
                PayloadSubsystem(capacity_kg=100.0),
                HealthSubsystem(wear_rate=0.1),
                AutonomySubsystem(),
                ThermalSubsystem(),
                AttitudeSubsystem(),
                EnvironmentSubsystem(),
                ResourceSubsystem({"water": 80.0})):
        bus.register(sub)
    return bus


@pytest.fixture()
def rig():
    bus = _full_bus()
    injector = FaultInjector(bus)
    controller = SubsystemPlatformController("sub-1", bus)
    return bus, injector, controller


def _controller(bus):
    return SubsystemPlatformController("sub-1", bus)


class TestNewSubsystems:
    def test_thermal_overheat_fault_and_recovery(self):
        thermal = ThermalSubsystem(overheat_limit=60.0)
        thermal.add_heat(70.0)                    # -> 90 > limit
        assert thermal.is_overheating()
        assert thermal.overheat_events == 1
        thermal.handle("set_cooling", {"on": True})
        for t in range(1, 40):
            thermal.tick(t)
        assert not thermal.is_overheating()

    def test_attitude_rate_limits_and_clamps(self):
        att = AttitudeSubsystem()
        att.handle("apply_rates", {"pitch_rate": 500.0,
                                   "roll_rate": -500.0})
        state = att.status()
        assert state["pitch"] == 10.0             # clamped to MAX_RATE
        assert state["roll"] == -10.0

    def test_environment_life_support(self):
        env = EnvironmentSubsystem()
        env.handle("set_scrubber", {"on": False})
        for t in range(1, 40):
            env.tick(t)
        assert not env.is_safe()                  # o2 decayed below safe
        env.handle("set_scrubber", {"on": True})
        env.handle("repressurize", {"target": 101.3})
        for t in range(40, 80):
            env.tick(t)
        assert env.o2_pct >= 17.0

    def test_resource_transfer_respects_capacity(self):
        res = ResourceSubsystem({"water": 50.0})
        moved = res.handle("transfer_out",
                           {"resource": "water", "amount": 20.0})
        assert moved == 20.0
        with pytest.raises(RuntimeError):
            res.handle("transfer_in", {"resource": "unobtainium",
                                       "amount": 5.0})


class TestFaultInjection:
    @pytest.fixture()
    def rig(self):
        bus = _full_bus()
        injector = FaultInjector(bus)
        controller = _controller(bus)
        return bus, injector, controller

    def test_failed_subsystem_refuses_commands(self, rig):
        bus, injector, ctrl = rig
        injector.fail_subsystem("sensors", "test")
        result = ctrl.execute_command(
            Command("sensors", "scan", {"targets": 2}))
        assert not result.success
        assert "disabled" in result.reason

    def test_engine_failure_blocks_restart(self, rig):
        bus, injector, ctrl = rig
        injector.engine_failure()
        result = ctrl.execute_command(Command(
            "propulsion", "start_engine"))
        assert not result.success

    def test_fuel_leak_drains_over_ticks(self, rig):
        bus, injector, ctrl = rig
        prop = bus.get("propulsion")
        start = prop.fuel
        injector.fuel_leak(rate=2.0)
        for t in range(5):
            injector.tick(t)
        assert prop.fuel < start
        injector.seal_leak()

    def test_power_depletion_recorded(self, rig):
        bus, injector, ctrl = rig
        injector.power_depletion()
        assert bus.get("power").battery_pct == 0.0
        assert any("depleted" in f["reason"]
                   for f in bus.get("power").faults)

    def test_sensor_blind_returns_empty_readings(self, rig):
        bus, injector, ctrl = rig
        injector.sensor_blind()
        reading = bus.get("sensors").handle("scan", {"targets": 3})
        assert reading["readings"] == {}
        assert reading["degraded"] is True

    def test_communication_blackout(self, rig):
        bus, injector, ctrl = rig
        injector.communication_blackout()
        result = ctrl.execute_command(Command(
            "communications", "transmit",
            {"recipient": "hq", "content": {"x": 1}}))
        assert not result.success

    def test_overheat_injection(self, rig):
        bus, injector, ctrl = rig
        injector.overheat(95.0)
        assert bus.get("thermal").is_overheating()

    def test_navigation_failure_clears_destination(self, rig):
        bus, injector, ctrl = rig
        bus.get("navigation").handle("set_destination",
                                     {"position": [9.0, 9.0]})
        injector.navigation_failure()
        assert bus.get("navigation").destination is None

    def test_degradation_accumulates(self, rig):
        bus, injector, ctrl = rig
        injector.degrade(30.0)
        injector.degrade(30.0)
        assert bus.get("health").wear == pytest.approx(60.0)

    def test_conflicting_command_detection(self, rig):
        bus, injector, ctrl = rig
        history = [
            Command("propulsion", "set_throttle", {"value": 0.8}),
            Command("propulsion", "set_throttle", {"value": -0.4}),
        ]
        conflicts = injector.detect_conflicts(history)
        assert len(conflicts) == 1
        assert conflicts[0]["parameter"] == "value"

    def test_invalid_command_fails_cleanly(self, rig):
        bus, injector, ctrl = rig
        result = ctrl.execute_command(
            Command("propulsion", "warp_drive", {}))
        assert not result.success
        assert "unknown action" in result.reason


class TestUnifiedPlatformState:
    def test_state_contains_all_standard_sections(self, rig):
        bus, _injector, ctrl = rig
        state = ctrl.get_state()
        for section in ("timestamp", "position", "velocity", "orientation",
                        "subsystem_states", "resources", "health",
                        "active_faults", "active_tasks"):
            assert section in state, section

    def test_faults_surface_in_state(self, rig):
        bus, injector, ctrl = rig
        injector.power_depletion()
        state = ctrl.get_state()
        assert state["health"]["active_fault_count"] >= 1
        assert any(f["subsystem"] == "power"
                   for f in state["active_faults"])


class TestUclCommandBusUnification:
    def test_single_authoritative_path(self, rig):
        """Commands through the UCL controller and directly through the
        bus must hit the SAME subsystem instance."""
        bus, injector, ctrl = rig
        before = len(bus.get("autonomy").task_queue)
        ctrl.execute_command(Command(
            "autonomy", "enqueue_task", {"task": {"kind": "survey"}}))
        assert len(bus.get("autonomy").task_queue) == before + 1

    def test_world_records_command_history(self, rig):
        from sandbox.ucl import WorldModel

        world = WorldModel()
        bus = _full_bus()
        ctrl = SubsystemPlatformController("sub-x", bus,
                                           world_model=world)
        ctrl.execute_command(Command("propulsion", "start_engine"))
        kinds = [c["message"].get("kind")
                 for c in world.communications]
        assert "command" in kinds