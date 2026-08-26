# Copyright (c) Ultrone Contributors. All rights reserved.
"""Tests for the Universal Control Layer (unified simulation platform
control) -- capability model, adapters, world model, mission system, and
the SIMULATION SAFETY BOUNDARY."""

import pytest

from sandbox.ucl import (
    ADAPTERS,
    Capability,
    CapabilityModel,
    Mission,
    SimulationLab,
)


@pytest.fixture(scope="module")
def lab():
    return SimulationLab(seed=0)


class TestCapabilityModel:
    def test_sheets_are_data_driven(self):
        assert CapabilityModel.supports("delivery_drone", "move")
        assert CapabilityModel.supports("eo_satellite", "communicate")
        assert not CapabilityModel.supports("network_sensor", "move")
        assert not CapabilityModel.supports("unknown_kind", "sense")

    def test_every_registered_machine_kind_has_a_sheet(self, lab):
        for ctrl in lab.controllers.values():
            sheet = CapabilityModel.sheet(ctrl.machine.KIND)
            assert sheet["capabilities"], ctrl.machine.KIND

    def test_nine_capability_types_exist(self):
        expected = {"sense", "move", "communicate", "navigate", "track",
                    "observe", "manage_power", "manage_payload",
                    "execute_task"}
        assert {c.value for c in Capability} == expected


class TestPlatformController:
    def test_supports_reflects_sheet(self, lab):
        drone = lab.controller("uav-1")
        sensor = lab.controller("cyber-1")
        assert drone.supports("move") and drone.supports("manage_payload")
        assert sensor.supports("observe")
        assert not sensor.supports("move")

    def test_domains_cover_all_five_plus_facility(self, lab):
        assert set(lab.domains_covered()) == {
            "air", "land", "sea", "space", "cyber", "facility"}

    def test_move_is_interlocked_by_the_machine(self, lab):
        drone_ctrl = lab.controller("uav-1")
        assert drone_ctrl.move({"vx": 99.0, "vy": 0.0, "vz": 0.0}) is False

    def test_manage_system_routes_through_interlock(self, lab):
        cnc_ctrl = lab.controller("cnc-1")
        # Closing the door is fine...
        assert cnc_ctrl.manage_system(
            {"action": "door", "args": [False, 1]}) is True
        # ...and then the spindle starts.
        assert cnc_ctrl.manage_system(
            {"action": "spindle", "args": [True, 9000, 2, 1.0]}) is True
        # Opening the door while the spindle runs is REFUSED.
        assert cnc_ctrl.manage_system(
            {"action": "door", "args": [True, 3]}) is False
        cnc_ctrl.manage_system({"action": "spindle", "args": [False, 0, 4]})
        cnc_ctrl.manage_system({"action": "door", "args": [True, 5]})

    def test_execute_task_produce_on_cnc_and_conveyor(self, lab):
        assert lab.controller("cnc-1").execute_task(
            {"type": "produce", "quantity": 5}, max_ticks=200)["success"]
        assert lab.controller("conv-1").execute_task(
            {"type": "produce", "quantity": 15}, max_ticks=300)["success"]

    def test_execute_task_navigate_drone(self, lab):
        result = lab.controller("uav-1").execute_task(
            {"type": "navigate", "to": [12.0, 10.0]}, max_ticks=200)
        assert result["success"]


class TestAdapters:
    def test_five_domain_adapters_plus_facility(self):
        assert {a.DOMAIN for a in ADAPTERS} == {
            "air", "land", "sea", "space", "cyber", "facility"}

    def test_sensor_scan_via_universal_interface(self, lab):
        reading = lab.controller("cyber-1").execute_task({"type": "scan"})
        assert reading["success"]
        assert "readings" in reading["reading"]


class TestWorldModel:
    def test_observations_recorded_per_entity(self, lab):
        for platform_id in ("uav-1", "usv-1", "sat-1"):
            snap = lab.world.observe(platform_id)
            assert snap is not None
            assert snap.state

    def test_domain_filtered_observations(self, lab):
        air_obs = lab.world.observations_by_domain("air")
        assert len(air_obs) == 1
        assert air_obs[0].entity_id == "uav-1"

    def test_communications_logged(self, lab):
        before = len(lab.world.communications)
        lab.controller("uav-1").communicate({"status": "on station"})
        assert len(lab.world.communications) == before + 1


class TestMissionSystem:
    def test_capability_based_assignment(self, lab):
        mission = Mission(
            "M-cap", "needs a moving payload platform",
            frozenset({Capability.MOVE, Capability.MANAGE_PAYLOAD}))
        lab.planner.assign(mission)
        assert mission.status == "ASSIGNED"
        assert "uav-1" in mission.assigned
        assert "cyber-1" not in mission.assigned

    def test_infeasible_when_no_platform_qualifies(self, lab):
        mission = Mission("M-impossible", "needs tracking",
                          frozenset({Capability.TRACK}))
        lab.planner.assign(mission)
        assert mission.status == "INFEASIBLE"

    def test_end_to_end_multi_domain_mission(self, lab):
        mission = Mission("M-multi", "reposition air+land",
                          frozenset({Capability.MOVE}))
        report = lab.run_mission(mission, {
            "uav-1": {"type": "navigate", "to": [10.0, 10.0]},
            "ugv-1": {"type": "navigate", "to": [8.0, 6.0]},
        }, max_ticks=250)
        assert report["mission"]["status"] == "COMPLETE"
        assert report["all_succeeded"]
        assert report["hard_violations"] == 0

    def test_mission_reproducible_given_seed(self):
        plan = {"uav-1": {"type": "navigate", "to": [12.0, 12.0]}}
        r1 = SimulationLab(seed=9).run_mission(
            Mission("M", "nav", frozenset({Capability.MOVE})),
            dict(plan), max_ticks=150)
        r2 = SimulationLab(seed=9).run_mission(
            Mission("M", "nav", frozenset({Capability.MOVE})),
            dict(plan), max_ticks=150)
        assert (r1["results"]["uav-1"]["final_dist"]
                == r2["results"]["uav-1"]["final_dist"])


class TestSimulationSafetyBoundary:
    """The universal layer terminates at simulated machines."""

    def test_module_imports_only_stdlib_and_sandbox(self):
        import pathlib

        source = pathlib.Path(
            __file__).resolve().parent.parent / "sandbox" / "ucl.py"
        forbidden_roots = ("agents", "brain", "core", "sim",
                           "ultrone_hitl", "research_db")
        bad = []
        for line in source.read_text(encoding="utf-8").splitlines():
            s = line.strip()
            if not s.startswith(("import ", "from ")):
                continue
            root = s.split()[1].split(".")[0]
            if root in forbidden_roots:
                bad.append(s)
        assert bad == []

    def test_every_controlled_machine_is_a_sandbox_instance(self, lab):
        import sandbox.machines as m

        for machine in lab.machines:
            assert type(machine).__module__ == m.__name__

    def test_no_realworld_transport_markers_in_ucl(self):
        import pathlib

        source = pathlib.Path(
            __file__).resolve().parent.parent / "sandbox" / "ucl.py"
        low = source.read_text(encoding="utf-8").lower()
        for marker in ("serial", "socket", "mqtt", "can_bus", "gpio",
                       "requests.", "urllib"):
            assert marker not in low, f"transport marker found: {marker}"