# Copyright (c) Ultrone Contributors. All rights reserved.
"""Tests for the industrial machine zoo + universal operator agent."""

import pytest

from sandbox.machines import MachineController, SafetyInterlock
from sandbox.machines_industrial import (
    ConfigurableMachine,
    ElevatorBank,
    KILN_SPEC,
    MIXER_SPEC,
    WindTurbine,
    build_industrial_plant,
    run_industrial_machine_suite,
)


class TestWindTurbine:
    def test_generation_and_pitch_cap(self):
        lock = SafetyInterlock()
        t = WindTurbine("wt", lock)
        assert t.command_brake(False, tick=1) is True
        for _ in range(60):
            t.step(1)
        assert t.rotor_rpm > 0 and t.energy_kwh > 0

    def test_overspeed_pitch_refused(self):
        lock = SafetyInterlock()
        t = WindTurbine("wt2", lock)
        t.wind_mps = 24.0                       # near cut-out
        t.pitch_deg = 20.0                      # currently feathered some
        t.command_brake(False, tick=1)
        # Flattening pitch at high wind would overspeed -> refused.
        assert t.command_pitch(0.0, tick=2) is False
        assert "overspeed" in lock.events[-1].reason

    def test_restart_refused_above_cutout(self):
        lock = SafetyInterlock()
        t = WindTurbine("wt3", lock)
        t.wind_mps = 30.0
        assert t.command_brake(False, tick=1) is False
        assert t.brake_on is True


class TestElevatorBank:
    def test_dispatch_cycle_with_load(self):
        ctrl = MachineController()
        bank = ElevatorBank("eb", ctrl.interlock)
        ctrl.register(bank)
        assert bank.command_load(0, 600.0, tick=1)
        assert bank.command_door(0, False, tick=2)
        assert bank.command_go(0, 6, tick=3)
        for t in range(1, 40):
            ctrl.step_all(t)
        assert abs(float(bank.cars[0]["floor"]) - 6.0) < 1e-6
        assert bank.command_door(0, True, tick=99)
        assert bank.command_unload(0, 600.0, tick=100)

    def test_motion_with_door_open_refused(self):
        bank = ElevatorBank("eb2", SafetyInterlock())
        assert bank.command_go(0, 5, tick=1) is False
        assert "door" in bank.lock.events[-1].reason

    def test_overload_refused(self):
        bank = ElevatorBank("eb3", SafetyInterlock())
        bank.cars[0]["door_open"] = True
        assert bank.command_load(0, 1200.0, tick=1) is False


class TestConfigurableMachine:
    def test_generated_actuators_and_envelopes(self):
        kiln = ConfigurableMachine("k", SafetyInterlock(), KILN_SPEC)
        assert kiln.command_set_temp(900.0, tick=1) is True
        assert kiln.state["set_temp"] == 900.0
        assert kiln.command_set_temp(5000.0, tick=2) is False
        assert kiln.command_conveyor(True, tick=3) is True
        assert kiln.state["conveyor"] is True

    def test_dynamics_settle_toward_setpoint(self):
        ctrl = MachineController()
        kiln = ConfigurableMachine("k2", ctrl.interlock, KILN_SPEC)
        ctrl.register(kiln)
        kiln.command_set_temp(400.0, tick=0)
        for t in range(1, 200):
            ctrl.step_all(t)
        assert abs(float(kiln.state["temp"]) - 400.0) <= 5.0

    def test_enum_actuator_rejects_unknown_choice(self):
        mixer = ConfigurableMachine("m", SafetyInterlock(), MIXER_SPEC)
        assert mixer.command_mode("warp", tick=1) is False
        assert mixer.command_mode("mix", tick=2) is True

    def test_capability_discovery_sees_generated_commands(self):
        ctrl = MachineController()
        ctrl.register(ConfigurableMachine("kiln-x", ctrl.interlock,
                                          KILN_SPEC))
        caps = ctrl.capabilities_of("kiln-x")
        assert {"set_temp", "conveyor"} <= set(caps)

    def test_estop_gates_generated_actuators(self):
        lock = SafetyInterlock()
        mixer = ConfigurableMachine("m2", lock, MIXER_SPEC)
        lock.trigger_estop()
        assert mixer.command_speed(50.0, tick=1) is False


class TestIndustrialSuite:
    @pytest.fixture(scope="module")
    def report(self):
        return run_industrial_machine_suite(seed=0)

    def test_all_tasks_settle(self, report):
        assert report["all_settled"], report["tasks"]

    def test_zero_hard_violations(self, report):
        assert report["zero_hard_violations"]

    def test_negative_controls_refused(self, report):
        assert report["negative_controls_all_rejected"]

    def test_capability_discovery_ok(self, report):
        assert report["capability_discovery_ok"]

    def test_fingerprint_reproducible(self):
        a = run_industrial_machine_suite(seed=7)
        b = run_industrial_machine_suite(seed=7)
        assert a["fingerprint"] == b["fingerprint"]


class TestUniversalOperatorAgent:
    def _agent_on_plant(self):
        from agents.civilian import UniversalOperatorAgent

        ctrl = build_industrial_plant(seed=0)
        agent = UniversalOperatorAgent("uni-1", controller=ctrl)
        agent.attach_machine(ctrl.machines["hvac-1"])
        return agent, ctrl

    def test_drives_machines_via_dispatch_plan(self):
        agent, ctrl = self._agent_on_plant()
        result = agent.execute_mission({
            "type": "heat_then_verify",
            "steps": [
                {"machine": "kiln-1", "action": "set_temp",
                 "params": {"value": 300.0},
                 "wait_for": {"sensor": "temp", "op": "ge",
                              "value": 290.0}},
                {"machine": "mixer-1", "action": "mode",
                 "params": {"value": "mix"}},
                {"machine": "mixer-1", "action": "speed",
                 "params": {"value": 80.0}},
            ],
        })
        assert result["success"], result
        assert result["steps_completed"] == 3
        assert result["clean"]
        assert float(ctrl.machines["kiln-1"].state["temp"]) >= 290.0

    def test_interlocked_step_is_a_recorded_refusal(self):
        agent, ctrl = self._agent_on_plant()
        result = agent.execute_mission({
            "type": "bad_plan",
            "steps": [
                {"machine": "kiln-1", "action": "set_temp",
                 "params": {"value": 9999.0}},       # outside envelope
                {"machine": "mixer-1", "action": "mode",
                 "params": {"value": "mix"}},        # still fine
            ],
        })
        assert not result["success"]
        assert len(result["refusals"]) == 1
        assert result["steps_completed"] == 1

    def test_unknown_capability_refused_without_touching_machines(self):
        agent, _ctrl = self._agent_on_plant()
        result = agent.execute_mission({
            "type": "hallucinate",
            "steps": [{"machine": "kiln-1", "action": "teleport"}],
        })
        assert not result["success"]
        assert "unknown on" in result["refusals"][0]["reason"]
        assert agent.controller.hard_violations == 0

    def test_capability_sheet_covers_whole_zoo(self):
        agent, _ctrl = self._agent_on_plant()
        sheet = agent.capability_sheet()
        assert len(sheet) >= 13
        assert "velocity" in sheet["robot-1"]["capabilities"]
        assert "set_temp" in sheet["kiln-1"]["capabilities"]
