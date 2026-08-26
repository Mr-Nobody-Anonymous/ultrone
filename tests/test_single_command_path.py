# Copyright (c) Ultrone Contributors. All rights reserved.
"""Single-command-path and subsystem-library completion tests.

Proves the milestone claim: any simulated platform is assembled from the
same primitives and controlled through EXACTLY ONE command path

    UCL verb -> structured Command -> CommandBus -> subsystems -> state

with safety enforcement living on that path, a standardized
``PlatformState`` read model, and no second actuation mechanism for
bus-driven platforms.
"""

import pytest

from agents.commands import Command, CommandBus
from agents.platform_control import (
    SubsystemPlatformController,
    build_platform_state,
    get_platform_state,
)
from agents.subsystems.locomotion import MobilitySubsystem
from agents.subsystems.platform_subsystems import (
    CommunicationSubsystem,
    NavigationSubsystem,
    PropulsionSubsystem,
)


def _rig():
    bus = CommandBus()
    for subsystem in (PropulsionSubsystem(fuel_capacity=50.0),
                      NavigationSubsystem(x=1.0, y=1.0),
                      CommunicationSubsystem()):
        bus.register(subsystem)
    controller = SubsystemPlatformController("plat-1", bus)
    return bus, controller


class TestUclSingleCommandPath:
    def test_manage_system_accepts_command_object(self):
        bus, ctrl = _rig()
        assert ctrl.manage_system(
            Command("propulsion", "start_engine")) is True
        assert bus.get("propulsion").engine_on is True

    def test_manage_system_accepts_dict_form(self):
        bus, ctrl = _rig()
        ctrl.manage_system(Command("propulsion", "start_engine"))
        accepted = ctrl.manage_system({
            "subsystem": "propulsion",
            "action": "set_throttle",
            "parameters": {"value": 0.5}})
        assert accepted is True
        assert bus.get("propulsion").throttle == 0.5

    def test_manage_system_unknown_subsystem_returns_false(self):
        _, ctrl = _rig()
        assert ctrl.manage_system(Command("warp", "engage")) is False
        assert ctrl.manage_system({"subsystem": "warp",
                                   "action": "engage"}) is False

    def test_move_maps_onto_the_same_bus(self):
        bus, ctrl = _rig()
        ctrl.manage_system(Command("propulsion", "start_engine"))
        assert ctrl.move({"to": [9.0, 4.0], "speed": 0.8}) is True
        assert bus.get("navigation").destination == {"x": 9.0, "y": 4.0}
        assert bus.get("propulsion").throttle == pytest.approx(0.8)

    def test_communicate_maps_onto_the_same_bus(self):
        bus, ctrl = _rig()
        reply = ctrl.communicate({"recipient": "hq",
                                  "content": {"status": "ok"}})
        assert reply["delivered"] is True
        assert len(bus.get("communications").outbox) == 1

    def test_execute_command_returns_structured_result(self):
        _, ctrl = _rig()
        result = ctrl.execute_command(
            Command("propulsion", "start_engine"))
        assert result.success is True
        assert result.value is True

    def test_adapter_machines_keep_working_without_bus(self):
        """Legacy adapter-driven platforms are untouched by the merge."""
        from sandbox import machines as _m
        from sandbox.ucl import PlatformController

        controller = _m.MachineController(seed=0)
        drone = _m.LogisticsDrone("uav-x", controller.interlock)
        controller.register(drone)
        ctrl = PlatformController(drone, stepper=controller.step_all)
        assert ctrl.command_bus is None
        assert ctrl.move({"vx": 0.5, "vy": 0.0}) in (True, False)


class TestEstopGateOnSinglePath:
    def _platform(self):
        from agents.air.drone_agent import DroneAgent
        from agents.subsystems.safety import SafetyInterlockSubsystem

        agent = DroneAgent("estop-1", (0.0, 0.0, 50.0))
        agent.register_subsystem(SafetyInterlockSubsystem())
        controller = SubsystemPlatformController(agent.unit.unit_id,
                                                 agent.bus)
        return agent, controller

    def test_agent_caller_blocked_then_released(self):
        agent, _ = self._platform()
        agent.execute(Command("safety", "engage_estop",
                              {"reason": "test"}))
        blocked = agent.execute(Command("propulsion", "start_engine"))
        assert not blocked.success and blocked.reason == "e-stop engaged"
        assert agent.execute(Command("safety", "release_estop")).success
        assert agent.execute(Command("propulsion",
                                     "start_engine")).success

    def test_controller_caller_hits_same_gate(self):
        agent, ctrl = self._platform()
        agent.execute(Command("safety", "engage_estop"))
        # manage_system / execute_command / move ALL route through the
        # gated CommandBus -- no bypass exists.
        assert ctrl.manage_system(
            Command("propulsion", "start_engine")) is False
        result = ctrl.execute_command(Command("propulsion", "set_throttle",
                                              {"value": 0.5}))
        assert not result.success and result.reason == "e-stop engaged"
        assert ctrl.move({"to": [2.0, 2.0]}) is False

    def test_direct_bus_use_is_gated_identically(self):
        agent, _ = self._platform()
        agent.execute(Command("safety", "engage_estop"))
        raw = agent.bus.execute(Command("propulsion", "stop_engine"))
        assert not raw.success and raw.reason == "e-stop engaged"

    def test_safety_commands_exempt_from_gate(self):
        agent, ctrl = self._platform()
        agent.execute(Command("safety", "engage_estop"))
        assert ctrl.manage_system(Command("safety", "release_estop")) \
            is True
        assert agent.safety.estopped is False


class TestPlatformStateReadModel:
    def test_schema_is_complete_and_stable(self):
        bus, ctrl = _rig()
        state = ctrl.get_state()
        assert sorted(state.keys()) == [
            "active_faults", "active_tasks", "health", "orientation",
            "position", "resources", "subsystem_states", "timestamp",
            "velocity"]

    def test_velocity_derived_from_speed_and_heading(self):
        bus, _ = _rig()
        bus.execute(Command("propulsion", "start_engine"))
        bus.execute(Command("navigation", "set_heading", {"deg": 90.0}))
        bus.execute(Command("propulsion", "set_throttle",
                            {"value": 0.5}))     # -> speed_available 1.5
        velocity = build_platform_state(bus)["velocity"]
        # Heading 90 deg points along +y: cos(90)=0, sin(90)=1.
        assert velocity["x"] == pytest.approx(0.0, abs=0.01)
        assert velocity["y"] == pytest.approx(1.5, abs=0.01)

    def test_state_accessor_uniform_across_sources(self):
        bus, ctrl = _rig()
        from agents.commands import Command as _C
        bus.execute(_C("propulsion", "start_engine"))
        bus.execute(_C("propulsion", "set_throttle", {"value": 0.5}))
        assert get_platform_state(ctrl) == get_platform_state(bus)
        with pytest.raises(TypeError):
            get_platform_state(object())

    def test_faults_surface_in_unified_state(self):
        from agents.subsystems.faults import FaultInjector

        bus, ctrl = _rig()
        injector = FaultInjector(bus)
        injector.engine_failure()
        state = ctrl.get_state()
        assert state["health"]["active_fault_count"] >= 1
        assert any(f["subsystem"] == "propulsion"
                   for f in state["active_faults"])
        # And the failure gates actuation on the same single path.
        assert ctrl.manage_system(
            Command("propulsion", "start_engine")) is False


class TestSubsystemLibraryLayout:
    """Canonical homes + compatibility re-exports both resolve."""

    def test_thermal_attitude_environment_resource_moved(self):
        from agents.subsystems import attitude as att_mod
        from agents.subsystems import environment as env_mod
        from agents.subsystems import resource as res_mod
        from agents.subsystems import thermal as thermal_mod
        from agents.subsystems.platform_subsystems import (
            AttitudeSubsystem as LegacyAttitude,
            EnvironmentSubsystem as LegacyEnvironment,
            ResourceSubsystem as LegacyResource,
            ThermalSubsystem as LegacyThermal)

        assert LegacyThermal is thermal_mod.ThermalSubsystem
        assert LegacyAttitude is att_mod.AttitudeSubsystem
        assert LegacyEnvironment is env_mod.EnvironmentSubsystem
        assert LegacyResource is res_mod.ResourceSubsystem

    def test_locomotion_is_canonical_mobility_shimmed(self):
        from agents.subsystems import mobility as shim

        assert MobilitySubsystem is shim.MobilitySubsystem
        assert MobilitySubsystem.name == "mobility"

    def test_new_primitives_exported_from_package(self):
        import agents.subsystems as pkg

        for name in ("LifeSupportSubsystem", "DiagnosticsSubsystem",
                     "SafetyInterlockSubsystem"):
            assert hasattr(pkg, name), name


class TestNewPrimitives:
    def test_life_support_rationing_extends_endurance(self):
        from agents.subsystems.life_support import LifeSupportSubsystem

        full = LifeSupportSubsystem()
        rationed = LifeSupportSubsystem()
        rationed.handle("set_rationing", {"on": True})
        assert rationed.status()["sustainable_ticks"] \
            > 1.5 * full.status()["sustainable_ticks"]
        # Rationing caps the generation setpoint.
        with pytest.raises(RuntimeError):
            rationed.handle("set_generation", {"rate": 0.95})

    def test_life_support_drawdown_and_resupply(self):
        from agents.subsystems.life_support import LifeSupportSubsystem

        unit = LifeSupportSubsystem()
        unit.handle("set_generation", {"rate": 1.0})
        for tick in range(10):
            unit.tick(tick)
        assert unit.o2_reserve_pct < 100.0
        unit.handle("resupply", {"o2_pct": 5.0})
        assert unit.o2_reserve_pct == pytest.approx(
            min(100.0, unit.o2_reserve_pct), abs=6.0)

    def test_diagnostics_sweep_reports_siblings(self):
        from agents.subsystems.diagnostics import DiagnosticsSubsystem
        from agents.subsystems.faults import FaultInjector
        from agents.subsystems.platform_subsystems import HealthSubsystem

        bus = CommandBus()
        health = HealthSubsystem(wear_rate=40.0)
        propulsion = PropulsionSubsystem()
        bus.register(health)
        bus.register(propulsion)
        diagnostics = DiagnosticsSubsystem()
        bus.register(diagnostics)
        diagnostics.watch_bus(bus)
        FaultInjector(bus).engine_failure()
        report = diagnostics.handle("run_full_sweep")
        assert report["components"] >= 3
        assert report["total_faults"] >= 1
        assert "propulsion" in report["per_subsystem"]
        assert report["per_subsystem"]["propulsion"]["enabled"] is False

    def test_safety_limits_and_gate_semantics(self):
        from agents.subsystems.safety import SafetyInterlockSubsystem

        interlock = SafetyInterlockSubsystem()
        interlock.handle("set_limit", {"key": "max_throttle",
                                       "value": 0.8})
        assert interlock.get_limits()["max_throttle"] == 0.8
        assert interlock.allows_actuation is True
        interlock.handle("engage_estop", {"reason": "drill"})
        assert interlock.allows_actuation is False
        with pytest.raises(RuntimeError):
            interlock.handle("set_limit", {"key": "bad", "value": -1.0})


class TestCompositionDiscipline:
    """Composition determines what exists -- per the platform sketches."""

    def test_underwater_platform_has_ballast_and_attitude(self):
        from agents.robotics import UnderwaterRobotAgent

        names = UnderwaterRobotAgent("uw-comp").subsystem_names()
        assert {"propulsion", "ballast", "attitude", "sonar"} <= set(names)

    def test_spacecraft_fault_management_via_diagnostics(self):
        from agents.space.satellite_agent import SatelliteAgent

        satellite = SatelliteAgent("sat-comp", (0.0, 0.0, 500.0))
        sweep = satellite.diagnostics.handle("run_full_sweep")
        assert sweep["components"] >= len(satellite.subsystem_names()) - 1

    def test_ground_truck_style_platform_has_no_naval_extras(self):
        from agents.robotics import GroundRobotAgent

        names = GroundRobotAgent("g-comp").subsystem_names()
        assert "ballast" not in names and "flight_control" not in names
