# Copyright (c) Ultrone Contributors. All rights reserved.
"""Tests for the simulated machine-control capability (Sprint F)."""

import math

import pytest

from sandbox.machines import (
    ClimateUnit,
    MachineController,
    MobileRobot,
    ProcessTank,
    RoboticArm,
    SafetyInterlock,
    build_factory_floor,
    proportional,
    run_machine_control_suite,
)


class TestInterlocks:
    def test_joint_limits_rejected_and_recorded(self):
        lock = SafetyInterlock()
        arm = RoboticArm("a", lock)
        assert arm.command_move({"base": 400.0}, tick=1) is False
        assert lock.events[-1].reason.startswith("joint")
        assert arm.command_move({"base": 90.0}, tick=2) is True

    def test_velocity_cap_and_battery_gate(self):
        lock = SafetyInterlock()
        robot = MobileRobot("r", lock)
        assert robot.command_velocity(9.9, 0.0, tick=1) is False
        robot.battery = 0.0
        assert robot.command_velocity(0.5, 0.0, tick=2) is False

    def test_valve_and_mode_envelopes(self):
        lock = SafetyInterlock()
        tank = ProcessTank("t", lock)
        hvac = ClimateUnit("h", lock)
        assert tank.command_valve(150.0, tick=1) is False
        assert tank.command_valve(60.0, tick=2) is True
        assert hvac.command_mode("explode", tick=3) is False

    def test_estop_latches_until_cleared(self):
        lock = SafetyInterlock()
        arm = RoboticArm("a", lock)
        lock.trigger_estop()
        assert arm.command_move({"base": 10.0}, tick=1) is False
        lock.clear_estop()
        assert arm.command_move({"base": 10.0}, tick=2) is True


class TestMachineDynamics:
    def test_arm_converges_to_target(self):
        ctrl = MachineController()
        arm = RoboticArm("a", ctrl.interlock)
        ctrl.register(arm)
        arm.command_move({"elbow": 90.0}, tick=0)
        for t in range(1, 40):
            ctrl.step_all(t)
        assert abs(arm.joints["elbow"] - 90.0) < 0.01

    def test_robot_stays_in_arena_when_controlled(self):
        ctrl = build_factory_floor(seed=1)
        robot = ctrl.machines["robot-1"]
        for t in range(1, 50):
            dx, dy = 10 - robot.x, 10 - robot.y
            turn = (math.atan2(dy, dx) - robot.heading + math.pi) \
                % (2 * math.pi) - math.pi
            robot.command_velocity(0.5, max(-1, min(1, turn * 2)), t)
            ctrl.step_all(t)
            assert 0.0 <= robot.x <= MobileRobot.ARENA
            assert 0.0 <= robot.y <= MobileRobot.ARENA

    def test_tank_overflow_is_a_hard_violation(self):
        ctrl = MachineController()
        tank = ProcessTank("t", ctrl.interlock)
        ctrl.register(tank)
        tank.command_valve(100.0, tick=0)
        for t in range(1, 20):          # inflow 10 vs demand 4: rises fast
            ctrl.step_all(t)
        assert ctrl.hard_violations >= 1
        assert tank.level == ProcessTank.CAPACITY

    def test_conveyor_jams_are_deterministic(self):
        a = build_factory_floor(seed=5)
        b = build_factory_floor(seed=5)
        ca, cb = a.machines["conveyor-1"], b.machines["conveyor-1"]
        ca.command_speed(1.5, 0)
        cb.command_speed(1.5, 0)
        for t in range(1, 30):
            a.step_all(t)
            b.step_all(t)
            if ca.jammed:
                ca.command_clear_jam(t)
            if cb.jammed:
                cb.command_clear_jam(t)
        assert ca.items_produced == cb.items_produced


class TestControlPolicies:
    def test_proportional_clamps_to_max_step(self):
        assert proportional(0.0, 100.0, gain=1.0, max_step=5.0) == 5.0
        assert proportional(99.0, 100.0, gain=0.3) == pytest.approx(0.3)

    def test_hvac_setpoint_task_settles(self):
        from sandbox.machines import run_setpoint_task

        ctrl = build_factory_floor(seed=0)
        hvac = ctrl.machines["hvac-1"]
        result = run_setpoint_task(
            ctrl, "hvac-1", tick_limit=80,
            read=lambda: hvac.temperature,
            actuate=lambda out, t: hvac.command_mode(
                "heat" if out > 0.05 else "cool" if out < -0.05 else "off", t),
            target=21.0, tolerance=0.75, gain=0.12,
        )
        assert result["settled"] and result["settled_tick"] < 80


class TestMachineSuite:
    @pytest.fixture(scope="module")
    def report(self):
        return run_machine_control_suite(seed=0)

    def test_every_machine_kind_settles(self, report):
        assert report["all_settled"]
        assert set(report["tasks"]) == {
            "arm_positioning", "robot_navigation", "conveyor_throughput",
            "tank_level_hold", "hvac_setpoint",
        }

    def test_zero_hard_violations(self, report):
        assert report["zero_hard_violations"]

    def test_negative_controls_refused(self, report):
        assert report["negative_controls_all_rejected"]
        assert report["interlock_rejections_recorded"] >= 4

    def test_fingerprint_reproducible(self):
        a = run_machine_control_suite(seed=3)
        b = run_machine_control_suite(seed=3)
        assert a["fingerprint"] == b["fingerprint"]

    def test_five_machine_kinds_controlled(self, report):
        assert report["machines_controlled"] == 5


class TestAgentMachineIntegration:
    def test_general_agent_drives_a_machine_safely(self):
        from sandbox.agent import GeneralAgent

        agent = GeneralAgent(seed=0)
        agent.attach_machines(build_factory_floor(seed=0))
        hvac = agent.machines.machines["hvac-1"]
        result = agent.handle_machine_task(
            "M1", machine_id="hvac-1",
            read=lambda: hvac.temperature,
            actuate=lambda out, t: hvac.command_mode(
                "heat" if out > 0.05 else "cool" if out < -0.05 else "off", t),
            target=21.0, tolerance=0.75,
        )
        assert result.success and result.detail["clean"]
        assert agent.completed_goals == 1
        hits = agent.recall_about("machine")
        assert any("settled=True" in h for h in hits)

    def test_unsafe_operation_is_not_success(self):
        from sandbox.agent import GeneralAgent

        agent = GeneralAgent(seed=0)
        ctrl = MachineController()
        tank = ProcessTank("tank-x", ctrl.interlock)
        tank.level = 98.0                    # near overflow
        ctrl.register(tank)
        agent.attach_machines(ctrl)
        result = agent.handle_machine_task(
            "M2", machine_id="tank-x",
            read=lambda: tank.level,
            actuate=lambda out, t: tank.command_valve(out * 10 + 50, t),
            target=60.0, tolerance=2.0,
        )
        # Whether it settles or not, an envelope breach must fail the task.
        if ctrl.hard_violations > 0:
            assert not result.success