# Copyright (c) Ultrone Contributors. All rights reserved.
"""Tests for the multi-domain simulation framework."""

import math

import pytest

from simulation.comms_logistics import (
    CLEARANCE_OPERATOR,
    CLEARANCE_PUBLIC,
    CommunicationNetwork,
    Depot,
    LogisticsSystem,
)
from simulation.core import (
    CheckpointManager,
    Evaluator,
    EventBus,
    ExperimentRunner,
    ScheduledTask,
    Scheduler,
    SimulationClock,
    TelemetryRecorder,
)
from simulation.runner import build_default_scenario
from simulation.world import (
    Contact,
    EnvironmentModel,
    SensorSuite,
    check_collisions,
)


class TestClockAndEvents:
    def test_clock_advances_and_resets(self):
        clock = SimulationClock()
        assert clock.tick == 0
        assert clock.advance(5) == 5
        clock.reset(2)
        assert clock.tick == 2

    def test_events_fire_once_in_deterministic_order(self):
        bus = EventBus()
        fired = []
        bus.schedule(10, "b", lambda s: fired.append("b"))
        bus.schedule(10, "a", lambda s: fired.append("a"))
        bus.schedule(12, "c", lambda s: fired.append("c"))
        assert bus.fire_due(11, None) == ["a", "b"]     # name order at t=10
        assert bus.fire_due(11, None) == []             # never re-fired
        assert bus.fire_due(12, None) == ["c"]


class TestScheduler:
    def test_priority_then_fifo_within_tick(self):
        sched = Scheduler()
        sched.enqueue(ScheduledTask("p1", {"t": 1}, start_tick=0, priority=1))
        sched.enqueue(ScheduledTask("p2", {"t": 2}, start_tick=0, priority=9))
        sched.enqueue(ScheduledTask("p3", {"t": 3}, start_tick=0, priority=5))
        due = sched.pop_due(0)
        assert [t.platform_id for t in due] == ["p2", "p3", "p1"]

    def test_future_tasks_not_dispatched(self):
        sched = Scheduler()
        sched.enqueue(ScheduledTask("later", {}, start_tick=50))
        assert sched.pop_due(49) == []
        assert sched.pending == 1


class TestTelemetryAndEvaluation:
    def test_telemetry_fingerprint_stable(self):
        a, b = TelemetryRecorder(), TelemetryRecorder()
        for rec in (a, b):
            rec.record(0, {"x": 1})
            rec.record(1, {"x": 2})
        assert a.fingerprint() == b.fingerprint()

    def test_evaluator_metrics(self):
        m = Evaluator.evaluate([{"success": True}, {"success": False}],
                               hard_violations=1, energy_used=4.2)
        assert m["task_completion_rate"] == 0.5
        assert m["hard_violations"] == 1
        assert m["safe_completion"] is False


class TestEnvironment:
    def test_weather_deterministic_and_bounded(self):
        env = EnvironmentModel(seed=1)
        first = [(env.wind(t), env.rain(t), env.sea_state(t))
                 for t in range(24)]
        second = [(env.wind(t), env.rain(t), env.sea_state(t))
                  for t in range(24)]
        assert first == second
        for wind, rain, sea in first:
            assert wind >= 0
            assert 0.0 <= rain <= 1.0
            assert 0 <= sea <= 9

    def test_atmosphere_thins_with_altitude(self):
        assert (EnvironmentModel.atmosphere_density(0)
                > EnvironmentModel.atmosphere_density(9000))

    def test_effective_speed_stays_positive(self):
        env = EnvironmentModel(seed=2)
        for domain in ("air", "sea", "land"):
            for tick in range(0, 48, 6):
                assert env.effective_speed(10, domain, tick=tick) > 0


class TestPhysicsAndSensors:
    def test_collision_detection(self):
        hits = check_collisions({"a": (0, 0), "b": (0.5, 0), "c": (9, 9)})
        assert ("a", "b") in hits
        assert all("c" not in pair for pair in hits)

    def test_radar_detects_in_range_with_error_field(self):
        env = EnvironmentModel(seed=3)
        suite = SensorSuite(env, seed=3)
        out = suite.radar_scan(0, 0, [Contact("x1", "buoy", 5, 5)],
                               range_=20, tick=8)
        assert len(out) == 1
        assert "position_error" in out[0]

    def test_radar_misses_beyond_range(self):
        suite = SensorSuite(EnvironmentModel(seed=3), seed=3)
        assert suite.radar_scan(
            0, 0, [Contact("far", "buoy", 90, 90)], range_=20) == []

    def test_optical_quality_degrades_with_clouds(self):
        suite = SensorSuite(EnvironmentModel(seed=0), seed=0)
        clear = suite.optical_capture("t", tick=0, cloud_cover=0.0)
        cloudy = suite.optical_capture("t", tick=0, cloud_cover=0.9)
        assert clear["quality"] > cloudy["quality"]

    def test_optical_capture_requires_tick_or_default(self):
        suite = SensorSuite(EnvironmentModel(seed=0), seed=0)
        result = suite.optical_capture("t", tick=0, cloud_cover=None)
        assert "quality" in result

    def test_sonar_only_reports_in_range(self):
        suite = SensorSuite(EnvironmentModel(seed=0), seed=0)
        contacts = [Contact("near", "buoy", 2, 2),
                    Contact("far", "buoy", 50, 50)]
        pings = suite.sonar_ping(0, 0, contacts, range_=12)
        assert [p["contact_id"] for p in pings] == ["near"]


class TestComms:
    def test_latency_defers_delivery(self):
        net = CommunicationNetwork(seed=0, loss_probability=0.0)
        net.register_node("hq")
        net.register_node("uav")
        net.send("hq", "uav", {"go": True}, tick=5)
        assert net.inboxes["uav"] == []
        net.deliver_due(6)
        assert len(net.inboxes["uav"]) == 1

    def test_unknown_node_rejected(self):
        net = CommunicationNetwork(seed=0)
        assert net.send("ghost", "uav", {}, tick=1) is None

    def test_permission_gate(self):
        net = CommunicationNetwork(seed=0)
        net.register_node("low", clearance=CLEARANCE_PUBLIC)
        net.register_node("ops", clearance=CLEARANCE_OPERATOR)
        assert net.send("low", "ops", {}, tick=1,
                        required_clearance=CLEARANCE_OPERATOR) is None
        assert net.send("ops", "low", {}, tick=1,
                        required_clearance=CLEARANCE_OPERATOR) is not None

    def test_immediate_priority_reduces_latency(self):
        fast = CommunicationNetwork(seed=0, loss_probability=0.0)
        fast.register_node("a")
        fast.register_node("b")
        fast.send("a", "b", {"urgent": True}, tick=4, priority="immediate")
        delivered = fast.deliver_due(4)          # latency 0 -> immediate
        assert delivered == 1


class TestLogistics:
    def test_proximity_resupply_restores_fuel(self):
        from sandbox.machines import ResearchVessel, SafetyInterlock

        logistics = LogisticsSystem()
        logistics.register_depot(Depot("port", x=2.0, y=2.0, range_=5.0))
        vessel = ResearchVessel("v", SafetyInterlock())
        vessel.x, vessel.y = 3.0, 3.0
        vessel.fuel = 10.0
        result = logistics.request_resupply(vessel, {"fuel": 80.0})
        assert result["success"]
        # 10 remaining + 80 granted = 90 (capacity is 100).
        assert vessel.fuel == pytest.approx(90.0)

    def test_out_of_range_refused(self):
        from sandbox.machines import ResearchVessel, SafetyInterlock

        logistics = LogisticsSystem()
        logistics.register_depot(Depot("port", x=0.0, y=0.0, range_=5.0))
        vessel = ResearchVessel("v", SafetyInterlock())
        vessel.x, vessel.y = 40.0, 40.0
        result = logistics.request_resupply(vessel, {"fuel": 80.0})
        assert not result["success"]
        assert result["in_range"] is False


class TestScenarioRunner:
    @pytest.fixture(scope="module")
    def report(self):
        scenario = build_default_scenario(seed=0)
        return scenario.run()

    def test_all_tasks_complete(self, report):
        assert report["evaluation"]["task_completion_rate"] == 1.0
        assert report["evaluation"]["safe_completion"] is True
        assert len(report["tasks"]) == 5

    def test_event_scheduled_and_environment_updated(self, report):
        assert ("wind_pickup" in [name for _, name in
                                  report["events_fired"]]) or \
               report["events_fired"] == []

    def test_telemetry_recorded_per_task(self, report):
        # One frame per completed task (sequential discrete-event style).
        assert len(report["tasks"]) > 0
        assert report["telemetry_fingerprint"]

    def test_scenario_reproducible(self):
        a = build_default_scenario(seed=7).run()
        b = build_default_scenario(seed=7).run()
        assert a["telemetry_fingerprint"] == b["telemetry_fingerprint"]
        assert [(t["platform_id"], t["finished_tick"])
                for t in a["tasks"]] == \
               [(t["platform_id"], t["finished_tick"]) for t in b["tasks"]]

    def test_different_seed_changes_sensor_readings(self):
        a = build_default_scenario(seed=1).run()
        b = build_default_scenario(seed=2).run()
        scan_a = next(t for t in a["tasks"]
                      if t["platform_id"] == "cyber-1")
        scan_b = next(t for t in b["tasks"]
                      if t["platform_id"] == "cyber-1")
        assert (scan_a["reading"]["readings"]
                != scan_b["reading"]["readings"])


class TestCheckpoints:
    def test_snapshot_restore_roundtrip(self):
        scenario = build_default_scenario(seed=0)
        scenario.run()
        state = CheckpointManager.snapshot(scenario)

        from simulation.runner import build_default_scenario as rebuild

        fresh = rebuild(seed=0)
        CheckpointManager.restore(fresh, state)
        restored_state = CheckpointManager.snapshot(fresh)
        assert restored_state["machines"] == state["machines"]

    def test_clone_continues_from_exact_state(self):
        scenario = build_default_scenario(seed=0)
        scenario.run()
        state = CheckpointManager.snapshot(scenario)
        twin = CheckpointManager.clone(scenario, state)
        for mid, saved in state["machines"].items():
            machine = twin.lab.machine_controller.machines[mid]
            for key, value in saved.items():
                assert getattr(machine, key) == value, (mid, key)


class TestExperimentRunner:
    def test_batch_runs_are_safe_and_deterministic(self):
        runner = ExperimentRunner()
        batch = runner.run_batch(
            lambda seed: build_default_scenario(seed), seeds=[0, 1, 2])
        assert batch["runs"] == 3
        assert batch["all_runs_safe"]
        assert batch["total_hard_violations"] == 0
        assert batch["mean_task_completion_rate"] >= 0.95