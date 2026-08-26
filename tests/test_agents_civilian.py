# Copyright (c) Ultrone Contributors. All rights reserved.
"""Tests for the civilian machine-operator domain in ``agents/``."""

import pytest

from data.entities import DomainType


@pytest.fixture(scope="module", autouse=True)
def _registered():
    import agents.civilian.factory  # noqa: F401 -- auto-registers on import


class TestRegistration:
    def test_civilian_types_registered_under_general_domain(self):
        from agents.registry import list_agent_types

        types = list_agent_types(DomainType.GENERAL)
        assert {"inspection_robot", "warehouse_arm",
                "process_operator"} <= set(types)

    def test_descriptions_declare_non_weaponized(self):
        from agents.registry import get_agent_class  # sanity: resolvable
        from agents.registry import _default_registry

        for agent_type in ("inspection_robot", "warehouse_arm",
                           "process_operator"):
            reg = _default_registry._agents[agent_type]
            assert "non-weaponized" in reg.description
            assert "engage" not in reg.capabilities
        # Resolving classes works.
        assert get_agent_class("inspection_robot") is not None


class TestGovernance:
    def _all_classes(self):
        from agents.civilian import (
            InspectionRobotAgent,
            ProcessOperatorAgent,
            WarehouseArmAgent,
        )

        return [InspectionRobotAgent, WarehouseArmAgent,
                ProcessOperatorAgent]

    def test_no_engage_capability_anywhere(self):
        from agents.base_agent import AgentCapability

        for cls in self._all_classes():
            agent = cls(unit_id=f"x-{cls.MACHINE_KIND}")
            assert not agent.can_perform(AgentCapability.ENGAGE)

    def test_capabilities_are_sense_and_communicate_only(self):
        from agents.base_agent import AgentCapability

        for cls in self._all_classes():
            agent = cls(unit_id=f"x-{cls.MACHINE_KIND}")
            assert set(agent.capabilities) == {
                AgentCapability.SENSE, AgentCapability.COMMUNICATE,
            }

    def test_team_and_domain_marked_civilian(self):
        from agents.civilian import InspectionRobotAgent

        agent = InspectionRobotAgent(unit_id="civ-1")
        assert agent.unit.team == "civilian"
        assert agent.unit.domain is DomainType.GENERAL


class TestInspectionRobot:
    def test_patrol_reaches_all_waypoints_without_violations(self):
        from agents.civilian import InspectionRobotAgent
        from sandbox.machines import MachineController, MobileRobot

        ctrl = MachineController(seed=0)
        agent = InspectionRobotAgent("insp-1", controller=ctrl)
        robot = MobileRobot("r-civ", ctrl.interlock)
        agent.attach_machine(robot)
        result = agent.execute_mission({
            "type": "patrol",
            "waypoints": [(8, 8), (15, 4), (10, 14)],
            "tolerance": 0.5,
        })
        assert result["success"]
        assert result["waypoints_reached"] == 3
        assert result["hard_violations"] == 0
        assert len(agent.mission_log) == 1

    def test_estop_fails_mission_safely(self):
        from agents.civilian import InspectionRobotAgent
        from sandbox.machines import MachineController, MobileRobot

        ctrl = MachineController(seed=0)
        agent = InspectionRobotAgent("insp-2", controller=ctrl)
        agent.attach_machine(MobileRobot("r2", ctrl.interlock))
        ctrl.interlock.trigger_estop()
        result = agent.execute_mission({
            "type": "patrol", "waypoints": [(5, 5)], "tolerance": 0.5,
        })
        assert not result["success"]


class TestWarehouseArm:
    def test_position_and_gripper_mission(self):
        from agents.civilian import WarehouseArmAgent
        from sandbox.machines import MachineController, RoboticArm

        ctrl = MachineController(seed=0)
        agent = WarehouseArmAgent("arm-op", controller=ctrl)
        arm = RoboticArm("a-civ", ctrl.interlock)
        agent.attach_machine(arm)
        result = agent.execute_mission({
            "type": "position",
            "joints": {"base": 90.0, "shoulder": -30.0, "elbow": 60.0},
            "gripper": "closed",
        })
        assert result["success"]
        assert result["settled"] is True
        assert result["gripper"] == "closed"
        assert abs(result["joints_final"]["base"] - 90.0) < 0.01

    def test_out_of_envelope_mission_refused_by_interlock(self):
        from agents.civilian import WarehouseArmAgent
        from sandbox.machines import MachineController, RoboticArm

        ctrl = MachineController(seed=0)
        agent = WarehouseArmAgent("arm-op2", controller=ctrl)
        agent.attach_machine(RoboticArm("a2", ctrl.interlock))
        result = agent.execute_mission({
            "type": "position", "joints": {"shoulder": 500.0},
        })
        assert not result["success"]
        assert "interlock" in result["reason"]

    def test_take_turn_steps_the_machine(self):
        from agents.civilian import WarehouseArmAgent
        from sandbox.machines import MachineController, RoboticArm

        ctrl = MachineController(seed=0)
        agent = WarehouseArmAgent("arm-op3", controller=ctrl)
        arm = RoboticArm("a3", ctrl.interlock)
        agent.attach_machine(arm)
        arm.command_move({"elbow": 45.0}, tick=0)
        before = arm.joints["elbow"]
        agent.take_turn({"tick": 1}, messages=[])
        assert arm.joints["elbow"] != before


class TestProcessOperator:
    @pytest.fixture()
    def operator(self):
        from agents.civilian import ProcessOperatorAgent
        from sandbox.machines import (
            ClimateUnit,
            ConveyorLine,
            MachineController,
            ProcessTank,
        )

        ctrl = MachineController(seed=0)
        op = ProcessOperatorAgent("proc-1", controller=ctrl)
        op.attach_tank(ProcessTank("tank-civ", ctrl.interlock))
        op.attach_conveyor(ConveyorLine("conv-civ", ctrl.interlock))
        op.attach_climate(ClimateUnit("hvac-civ", ctrl.interlock))
        return op

    def test_hold_level_mission(self, operator):
        result = operator.execute_mission(
            {"type": "hold_level", "target": 60.0})
        assert result["success"]
        assert result["clean"]
        assert result["held_ticks"] >= 10

    def test_produce_mission_handles_jams(self, operator):
        result = operator.execute_mission({"type": "produce", "quantity": 20})
        assert result["success"]
        assert result["items"] >= 20

    def test_climate_mission_converges(self, operator):
        result = operator.execute_mission({"type": "set_climate",
                                           "target": 21.0})
        assert result["success"]
        assert abs(result["final_temperature"] - 21.0) <= 0.75

    def test_unknown_mission_type_rejected_cleanly(self, operator):
        result = operator.execute_mission({"type": "self_destruct"})
        assert not result["success"]
        assert "unknown mission type" in result["reason"]

    def test_estop_latches_process_control(self, operator):
        operator.controller.interlock.trigger_estop()
        result = operator.execute_mission({"type": "produce", "quantity": 5})
        assert not result["success"]
        assert result["reason"] == "e-stop latched"


class TestCraneOperator:
    @pytest.fixture()
    def crane_setup(self):
        from agents.civilian import CraneOperatorAgent
        from sandbox.machines import MachineController, OverheadCrane

        ctrl = MachineController(seed=0)
        agent = CraneOperatorAgent("crane-op", controller=ctrl)
        crane = OverheadCrane("crane-civ", ctrl.interlock)
        agent.attach_machine(crane)
        return agent, crane, ctrl

    def test_lift_and_place_mission_succeeds(self, crane_setup):
        agent, crane, ctrl = crane_setup
        result = agent.execute_mission({
            "type": "lift_place",
            "pick": (10.0, 5.0),
            "place": (16.0, 8.0),
            "load_kg": 250.0,
        })
        assert result["success"], result
        assert result["load_delivered_kg"] == 250.0
        assert abs(crane.bridge - 16.0) <= 0.2
        assert abs(crane.trolley - 8.0) <= 0.2

    def test_overloaded_hook_refused(self, crane_setup):
        agent, _crane, _ctrl = crane_setup
        result = agent.execute_mission({
            "type": "lift_place",
            "pick": (10.0, 5.0), "place": (16.0, 8.0),
            "load_kg": 900.0,                     # over the 500 kg rating
        })
        assert not result["success"]
        assert result["hard_violations"] == 0     # refused, never breached

    def test_sway_never_becomes_a_violation(self, crane_setup):
        agent, _crane, ctrl = crane_setup
        agent.execute_mission({
            "type": "lift_place",
            "pick": (12.0, 7.0), "place": (4.0, 3.0),
            "load_kg": 400.0,
        })
        # Sway refusals are recorded as rejections, never as breaches.
        reasons = [e.reason for e in ctrl.interlock.events]
        assert any("sway" in r for r in reasons)
        assert ctrl.hard_violations == 0


class TestMachinist:
    def test_production_run_with_tool_lifecycle(self):
        from agents.civilian import MachiningAgent
        from sandbox.machines import CNCMachine, MachineController

        ctrl = MachineController(seed=0)
        agent = MachiningAgent("cnc-op", controller=ctrl)
        cnc = CNCMachine("cnc-civ", ctrl.interlock)
        agent.attach_machine(cnc)
        result = agent.execute_mission(
            {"type": "machine_parts", "quantity": 30,
             "rpm": 9000, "feed_rate": 1.5})
        assert result["success"]
        assert result["parts_produced"] >= 30
        assert cnc.spindle_on is False           # shuts down after the run
        assert cnc.door_open is True             # reopens for unloading

    def test_spindle_with_door_open_is_refused(self):
        from sandbox.machines import CNCMachine, SafetyInterlock

        lock = SafetyInterlock()
        cnc = CNCMachine("cnc-x", lock)
        assert cnc.command_spindle(True, 9000, tick=1) is False
        assert lock.events[-1].reason.startswith("door")
        assert cnc.command_door(open_=False, tick=2) is True
        assert cnc.command_spindle(True, 9000, tick=3) is True

    def test_tool_wear_forces_service(self):
        from sandbox.machines import CNCMachine, SafetyInterlock

        cnc = CNCMachine("cnc-y", SafetyInterlock())
        cnc.command_door(False, tick=0)
        cnc.command_spindle(True, 9000, tick=1, feed_rate=10.0)
        for t in range(1, 30):                    # wear accumulates past limit
            cnc.step(t)
        assert cnc.needs_tool_service
        assert cnc.command_spindle(True, 9000, tick=99) is False   # blocked
        assert cnc.command_tool_change(tick=100) is False          # spindle on
        cnc.command_spindle(False, 0, tick=101)
        assert cnc.command_tool_change(tick=102) is True


class TestDeliveryDrone:
    def test_delivery_round_trip(self):
        from agents.civilian import DeliveryDroneAgent
        from sandbox.machines import LogisticsDrone, MachineController

        ctrl = MachineController(seed=0)
        agent = DeliveryDroneAgent("drone-op", controller=ctrl)
        drone = LogisticsDrone("d-civ", ctrl.interlock)
        agent.attach_machine(drone)
        result = agent.execute_mission({
            "type": "deliver", "destination": (14.0, 14.0),
            "payload_kg": 1.5, "altitude": 10.0,
        })
        assert result["success"], result
        assert result["delivered"]
        assert result["returned_home"]
        assert result["final_battery_pct"] > drone.BATTERY_RESERVE_PCT

    def test_no_fly_zone_blocks_delivery(self):
        from agents.civilian import DeliveryDroneAgent
        from sandbox.machines import LogisticsDrone, MachineController

        ctrl = MachineController(seed=0)
        agent = DeliveryDroneAgent("drone-op2", controller=ctrl)
        drone = LogisticsDrone("d2", ctrl.interlock)
        drone.declare_nofly_zone(8.0, 8.0, radius=4.0)  # walls off the path
        agent.attach_machine(drone)
        result = agent.execute_mission({
            "type": "deliver", "destination": (16.0, 16.0),
            "payload_kg": 1.0, "altitude": 10.0,
        })
        assert not result["delivered"]
        assert any(e.reason and "no-fly" in e.reason
                   for e in ctrl.interlock.events)

    def test_battery_reserve_enforced_in_flight(self):
        from sandbox.machines import LogisticsDrone, SafetyInterlock

        drone = LogisticsDrone("d3", SafetyInterlock())
        drone.battery_pct = 12.0                  # below reserve
        drone.z = 10.0                            # airborne
        assert drone.command_velocity(1.0, 0.0, 0.0, tick=1) is False
        drone.z = 0.0                             # landed: may recharge
        assert drone.command_recharge(tick=2) is True