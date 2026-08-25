# Copyright (c) Ultrone Contributors. All rights reserved.
"""Tests for controlled simulation fault injection (Sprint B-C)."""

import random

import pytest

from sim.fault_injection import (
    FaultSpec,
    FaultType,
    FaultyEnv,
    FaultySensorSuite,
)
from benchmarks.canonical.runner import run_scenario


class _FakeRecord:
    def __init__(self, sensor_type, position, confidence=0.8, dropped=False):
        self.sensor_type = sensor_type
        self.position = position
        self.confidence = confidence
        self.dropped = dropped


class _FakeSuite:
    """Minimal stand-in for core.pipeline.SensorSuite."""

    def generate(self, obs):
        return [
            _FakeRecord(t, (50.0 + i, 50.0, 0.0))
            for i, t in enumerate(["radar", "visual", "sigint"])
        ]


class TestSensorFaults:
    def test_dropout_removes_feeds_deterministically(self):
        suite = FaultySensorSuite(
            _FakeSuite(), (FaultSpec(FaultType.SENSOR_DROPOUT, probability=1.0),),
            random.Random(7),
        )
        records = suite.generate({})
        assert all(r.dropped for r in records)

    def test_no_dropout_when_probability_zero(self):
        suite = FaultySensorSuite(
            _FakeSuite(), (FaultSpec(FaultType.SENSOR_DROPOUT, probability=0.0),),
            random.Random(7),
        )
        records = suite.generate({})
        assert not any(r.dropped for r in records)

    def test_comms_loss_blacks_out_every_feed(self):
        suite = FaultySensorSuite(
            _FakeSuite(), (FaultSpec(FaultType.COMMS_LOSS, probability=1.0),),
            random.Random(1),
        )
        records = suite.generate({})
        assert len(records) == 3
        assert all(r.dropped for r in records)

    def test_noisy_observation_offsets_targeted_feed_only(self):
        suite = FaultySensorSuite(
            _FakeSuite(),
            (FaultSpec(
                FaultType.NOISY_OBSERVATION,
                probability=1.0, intensity=100.0, feed_type="sigint",
            ),),
            random.Random(3),
        )
        records = {r.sensor_type: r for r in suite.generate({})}
        assert abs(records["radar"].position[0] - 50.0) < 1e-9
        assert abs(records["sigint"].position[0] - 50.0) > 10.0  # conflicting
        # confidence penalized on the corrupted feed
        assert records["sigint"].confidence < 0.8

    def test_same_seed_same_fault_schedule(self):
        def run():
            suite = FaultySensorSuite(
                _FakeSuite(), (FaultSpec(FaultType.SENSOR_DROPOUT, probability=0.5),),
                random.Random(99),
            )
            return [r.dropped for r in suite.generate({})]

        assert run() == run()


class _FakeEnv:
    def __init__(self):
        self.calls = []

    def reset(self, *a, **k):
        return {
            "red_force": {"health": 100},
            "blue_assets": {"missiles": [{"ammo": 10, "fuel": 1.0, "position": [0, 0]}]},
            "supply_nodes": {},
        }

    def step(self, action):
        self.calls.append(action)
        obs = self.reset()
        return obs, -1.0 if action is None else 1.0, False, {}


class TestEnvFaults:
    def test_actuator_failure_degrades_to_noop(self):
        env = FaultyEnv(_FakeEnv(), (FaultSpec(
            FaultType.ACTUATOR_FAILURE, probability=1.0, asset_type="missiles",
        ),), random.Random(5))
        env.step({"action": "strike", "asset_type": "missiles"})
        assert env.base.calls[-1] is None
        assert env.stats["actuator_failure"] == 1

    def test_actuator_failure_respects_asset_filter(self):
        env = FaultyEnv(_FakeEnv(), (FaultSpec(
            FaultType.ACTUATOR_FAILURE, probability=1.0, asset_type="drones",
        ),), random.Random(5))
        action = {"action": "strike", "asset_type": "missiles"}
        env.step(action)
        assert env.base.calls[-1] == action  # unaffected asset passes through



class TestEnvFaultsContinued:
    def test_stale_observation_serves_cached_snapshot(self):
        env = FaultyEnv(_FakeEnv(), (FaultSpec(
            FaultType.STALE_OBSERVATION, probability=1.0,
        ),), random.Random(5))
        fresh = env.reset()
        fresh["red_force"]["health"] = 77  # world moved on
        stale = env.step(None)[0]
        assert stale["red_force"]["health"] != 77  # aged snapshot served
        assert env.stats["stale_observation"] >= 1

    def test_resource_degradation_scales_ammo_and_fuel(self):
        env = FaultyEnv(_FakeEnv(), (FaultSpec(
            FaultType.RESOURCE_DEGRADATION, probability=1.0, intensity=0.5,
        ),), random.Random(5))
        obs = env.reset()
        missile = obs["blue_assets"]["missiles"][0]
        assert missile["ammo"] == 5
        assert missile["fuel"] == pytest.approx(0.5)


class TestIntegrationWithPipeline:
    def test_pipeline_runs_end_to_end_under_all_faults(self):
        from benchmarks.canonical.scenarios import ScenarioSpec

        spec = ScenarioSpec(
            scenario_id="all_faults_smoke", description="", seed=11, n_steps=4,
            faults=(
                FaultSpec(FaultType.SENSOR_DROPOUT, probability=0.3),
                FaultSpec(FaultType.NOISY_OBSERVATION, probability=0.5, intensity=5.0),
                FaultSpec(FaultType.COMMS_LOSS, probability=0.2),
                FaultSpec(FaultType.ACTUATOR_FAILURE, probability=0.2),
                FaultSpec(FaultType.STALE_OBSERVATION, probability=0.2),
                FaultSpec(FaultType.RESOURCE_DEGRADATION, probability=1.0, intensity=0.9),
            ),
            human_policy="approve",
        )
        record = run_scenario(spec)
        assert record["failures"] == []
        assert record["metrics"]["steps"] == 4
        assert record["audit_chain_verified"] is True

    def test_low_resource_scenario_triggers_safety_rejections(self):
        from benchmarks.canonical.scenarios import SCENARIOS

        rec = run_scenario(SCENARIOS["low_resource_condition"])
        assert rec["metrics"]["safety_rejections"] >= 1
