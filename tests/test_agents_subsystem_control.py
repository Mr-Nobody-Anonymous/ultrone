# Copyright (c) Ultrone Contributors. All rights reserved.
"""Subsystem-level control tests for every simulated platform agent.

Covers: domain default compositions, structured command execution,
hierarchical capabilities, unified state view, telemetry, specialized
naval/space/cyber subsystems, and the robotics + infrastructure domains
(non-engagement safety guarantees included).
"""

import pytest

from agents.base_agent import AgentCapability
from agents.commands import Command
from agents.telemetry import TelemetryRecorder


# --------------------------------------------------------------------- #
# Air: the canonical drone subsystem tree                                 #
# --------------------------------------------------------------------- #
class TestDroneSubsystemControl:
    def _drone(self):
        from agents.air.drone_agent import DroneAgent

        return DroneAgent("d-test", (0.0, 0.0, 100.0))

    def test_default_air_composition(self):
        drone = self._drone()
        assert set(drone.subsystem_names()) == {
            "propulsion", "navigation", "flight_control", "sensors",
            "communications", "power", "payload", "health", "environment",
            "autonomy",
        }

    def test_structured_command_flow(self):
        drone = self._drone()
        assert drone.execute(
            Command("propulsion", "start_engine")).success
        throttle = drone.execute(
            Command("propulsion", "set_throttle", {"value": 0.65}))
        assert throttle.success and throttle.value == 0.65

    def test_flight_control_autopilot_integrates_altitude(self):
        drone = self._drone()
        drone.execute(Command("flight_control", "engage_autopilot"))
        drone.execute(Command("flight_control", "set_altitude",
                              {"meters": 150.0}))
        for tick in range(1, 30):
            drone.tick_platform(tick)
        assert drone.flight_control.altitude == pytest.approx(150.0,
                                                              abs=2.5)

    def test_unknown_action_fails_cleanly(self):
        drone = self._drone()
        result = drone.execute(Command("propulsion", "warp", {}))
        assert not result.success
        assert "unknown action" in result.reason

    def test_capability_tree_is_hierarchical(self):
        drone = self._drone()
        tree = drone.available_capabilities()
        assert tree["mobility"] == ["translation", "rotation", "altitude"]
        assert "task_execution" in tree["mission"]

    def test_state_snapshot_and_telemetry(self):
        drone = self._drone()
        drone.execute(Command("propulsion", "start_engine"))
        snapshot = drone.state_snapshot(tick=7)
        assert snapshot["timestamp"] == 7
        assert "propulsion" in snapshot["subsystem_states"]
        assert drone.platform_state.resources()["fuel"] > 0
        history = drone.command_history()
        assert history[-1]["action"] == "start_engine"
        assert history[-1]["success"] is True


# --------------------------------------------------------------------- #
# Sea: submarine ballast + sonar                                          #
# --------------------------------------------------------------------- #
class TestSubmarineSubsystems:
    def _submarine(self):
        from agents.sea.submarine_agent import SubmarineAgent

        return SubmarineAgent("s-test", (0.0, 0.0, -50.0))

    def test_naval_extras_registered(self):
        sub = self._submarine()
        assert {"ballast", "sonar"} <= set(sub.subsystem_names())
        assert sub.ballast.depth_m == pytest.approx(50.0)

    def test_dive_requires_ballast_fill(self):
        sub = self._submarine()
        refused = sub.execute(Command("ballast", "dive",
                                      {"depth_m": 120.0}))
        assert not refused.success          # no ballast yet
        sub.execute(Command("ballast", "fill_ballast", {"amount": 0.6}))
        assert sub.execute(Command("ballast", "dive",
                                   {"depth_m": 120.0})).success

    def test_depth_converges_to_target(self):
        sub = self._submarine()
        sub.execute(Command("ballast", "fill_ballast", {"amount": 0.6}))
        sub.execute(Command("ballast", "dive", {"depth_m": 90.0}))
        for tick in range(20):
            sub.tick_platform(tick)
        assert sub.ballast.depth_m == pytest.approx(90.0, abs=4.5)

    def test_sonar_modes(self):
        sub = self._submarine()
        passive = sub.execute(Command("sonar", "passive_listen",
                                      {"contacts": 2}))
        assert passive.success and "bearings" in passive.value
        ping = sub.execute(Command("sonar", "active_ping",
                                   {"contacts": 2}))
        assert ping.success and "ranges" in ping.value
        bad = sub.execute(Command("sonar", "set_mode",
                                  {"mode": "ultra"}))
        assert not bad.success


# --------------------------------------------------------------------- #
# Space: orbital navigation + attitude + thermal                          #
# --------------------------------------------------------------------- #
class TestSpacecraftSubsystems:
    def _satellite(self):
        from agents.space.satellite_agent import SatelliteAgent

        return SatelliteAgent("sat-test", (0.0, 0.0, 500.0))

    def test_space_composition(self):
        sat = self._satellite()
        for name in ("orbital_navigation", "thermal", "attitude", "power"):
            assert name in sat.subsystem_names()

    def test_burn_budget_enforced(self):
        sat = self._satellite()
        burn = sat.execute(Command("orbital_navigation", "execute_burn",
                                   {"delta_v": 20.0}))
        assert burn.value["delta_v_remaining"] == 80.0
        oversized = sat.execute(Command("orbital_navigation",
                                        "execute_burn",
                                        {"delta_v": 9999.0}))
        assert not oversized.success
        assert "delta-v" in oversized.reason

    def test_attitude_rate_limits_apply(self):
        sat = self._satellite()
        result = sat.execute(Command("attitude", "apply_rates",
                                     {"pitch_rate": 500.0}))
        assert result.value["pitch"] == 10.0     # clamped to MAX_RATE


# --------------------------------------------------------------------- #
# Cyber: computing-node subsystems and defensive controls                 #
# --------------------------------------------------------------------- #
class TestCyberNodeSubsystems:
    def _node(self):
        from agents.cyber.defend_agent import DefendAgent

        return DefendAgent("def-test", (0.0, 0.0, 0.0))

    def test_node_composition(self):
        node = self._node()
        assert set(node.subsystem_names()) >= {
            "compute", "storage", "network", "services", "authentication",
            "monitoring", "configuration", "defensive_controls", "health",
        }

    def test_defensive_posture_and_storage_limits(self):
        node = self._node()
        hardened = node.execute(Command("defensive_controls", "set_posture",
                                        {"level": "hardened"}))
        assert hardened.value == "hardened"
        overfill = node.execute(Command("storage", "write", {"gb": 10**6}))
        assert not overfill.success
        quarantine = node.execute(Command("defensive_controls",
                                          "quarantine_segment",
                                          {"segment": "lab-net"}))
        assert quarantine.success
        status = node.platform_state.subsystem("defensive_controls")
        assert status["quarantined_segments"] == ["lab-net"]

    def test_disabled_subsystem_refuses_via_result(self):
        from agents.subsystems.faults import FaultInjector

        node = self._node()
        injector = FaultInjector(node.bus)
        injector.fail_subsystem("authentication")
        result = node.execute(Command("authentication", "rotate_credentials",
                                      {"account": "admin"}))
        assert not result.success
        assert "disabled" in result.reason


# --------------------------------------------------------------------- #
# Robotics domain                                                         #
# --------------------------------------------------------------------- #
ROBOT_CLASSES = ["GroundRobotAgent", "AerialRobotAgent",
                 "UnderwaterRobotAgent", "IndustrialRobotAgent"]


class TestRoboticsDomain:
    @pytest.mark.parametrize("class_name", ROBOT_CLASSES)
    def test_robots_are_non_engaging_and_composed(self, class_name):
        import agents.robotics as robotics

        cls = getattr(robotics, class_name)
        robot = cls(unit_id=f"r-{cls.MACHINE_KIND}")
        assert not robot.can_perform(AgentCapability.ENGAGE)
        assert set(robot.capabilities) == {
            AgentCapability.SENSE, AgentCapability.COMMUNICATE}
        assert robot.capability_tree.covers({"task_execution"})
        assert len(robot.subsystem_names()) >= 5

    def test_ground_patrol_mission(self):
        from agents.robotics import GroundRobotAgent

        robot = GroundRobotAgent("g-test")
        result = robot.execute_mission({"waypoints": [[5.0, 0.0],
                                                      [10.0, 3.0]]})
        assert result["success"] is True
        assert result["waypoints_served"] == 2
        assert robot.mobility.odometry > 0

    def test_underwater_survey_dives_and_surfaces(self):
        from agents.robotics import UnderwaterRobotAgent

        robot = UnderwaterRobotAgent("u-test")
        result = robot.execute_mission({"waypoints": [[4.0, 4.0],
                                                      [8.0, 4.0]],
                                        "depth_m": 15.0})
        assert result["success"] is True
        assert result["final_depth_m"] == 0.0      # surfaced at end
        assert robot.ballast.surfaced

    def test_industrial_cycles(self):
        from agents.robotics import IndustrialRobotAgent

        result = IndustrialRobotAgent("i-test").execute_mission(
            {"cycles": 3, "part_kg": 4.0})
        assert result["success"] is True
        assert result["cycles_completed"] == 3


# --------------------------------------------------------------------- #
# Infrastructure domain                                                   #
# --------------------------------------------------------------------- #
INFRA_CLASSES = ["PowerGridAgent", "CommsInfrastructureAgent",
                 "IndustrialPlantAgent", "TransitNetworkAgent"]


class TestInfrastructureDomain:
    @pytest.mark.parametrize("class_name", INFRA_CLASSES)
    def test_nodes_are_non_engaging_and_registered(self, class_name):
        import agents.infrastructure as infrastructure
        from agents.registry import get_agent_class, list_agent_types

        cls = getattr(infrastructure, class_name)
        node = cls(unit_id=f"n-{cls.MACHINE_KIND}")
        assert not node.can_perform(AgentCapability.ENGAGE)
        assert set(node.capabilities) == {
            AgentCapability.SENSE, AgentCapability.COMMUNICATE}
        type_map = {t: get_agent_class(t) for t in list_agent_types()}
        registered = [t for t, c in type_map.items() if c is cls]
        assert registered, f"{cls.__name__} missing from registry"

    def test_power_dispatch_balances(self):
        from agents.infrastructure import PowerGridAgent

        grid = PowerGridAgent("p-test")
        result = grid.execute_mission({"demand_kw": 8.0})
        assert result["success"] is True
        assert result["supplied_kw"] == result["demand_kw"]

    def test_power_shortfall_raises_alert(self):
        from agents.infrastructure import PowerGridAgent

        grid = PowerGridAgent("p-short")
        grid.get_subsystem("resource").levels["stored_energy"] = 0.0
        result = grid.execute_mission({"demand_kw": 5.0})
        assert result["success"] is False
        assert grid.platform_state.subsystem("monitoring")[
            "open_alerts"] >= 1

    def test_comms_relay_roundtrip(self):
        from agents.infrastructure import CommsInfrastructureAgent

        node = CommsInfrastructureAgent("c-test")
        result = node.execute_mission({"recipients": ["alpha", "beta"],
                                       "message": {"hello": True}})
        assert result["success"] is True
        assert result["relayed"] == 2
        assert not node.network.connected       # disconnected after relay

    def test_transit_serves_all_stops(self):
        from agents.infrastructure import TransitNetworkAgent

        result = TransitNetworkAgent("t-test").execute_mission(
            {"route": [[3.0, 0.0], [6.0, 2.0], [9.0, 2.0]]})
        assert result["success"] is True
        assert result["stops_served"] == 3


# --------------------------------------------------------------------- #
# Telemetry module units                                                  #
# --------------------------------------------------------------------- #
class TestTelemetryRecorder:
    def test_ring_buffer_bounds(self):
        recorder = TelemetryRecorder(source_id="unit-x",
                                     snapshot_limit=3, command_limit=2)

        def fake_result():
            return type("R", (), {"subsystem": "s", "action": "a",
                                  "success": True, "reason": ""})()

        for i in range(6):
            recorder.record_snapshot({"tick": i}, i)
            recorder.record_command(fake_result(), tick=i)
        assert len(recorder.snapshots()) == 3
        assert len(recorder.commands()) == 2
        assert recorder.latest()["recorded_at"] == 5
        exported = recorder.export()
        assert exported["source_id"] == "unit-x"
        assert len(exported["snapshots"]) == 3


# --------------------------------------------------------------------- #
# Regression guard: legacy behavior intact                                #
# --------------------------------------------------------------------- #
class TestLegacyBehaviorPreserved:
    def test_drone_still_takes_turns_and_reports_capabilities(self):
        from agents.air.drone_agent import DroneAgent

        drone = DroneAgent("d-legacy", (1.0, 2.0, 3.0))
        assert drone.take_turn({}, []) == []
        assert drone.can_perform(AgentCapability.SENSE)
        assert isinstance(drone.to_dict(), dict)

    def test_registry_class_has_subsystem_control(self):
        from agents.registry import get_agent_class

        cls = get_agent_class("tank")
        agent = cls("t-reg", (0.0, 0.0, 0.0))
        assert "mobility" in agent.subsystem_names()
        assert agent.execute(Command("mobility", "set_mode",
                                     {"mode": "tracks"})).success