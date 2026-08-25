# Copyright (c) Ultrone Contributors. All rights reserved.
"""Tests for the canonical benchmark/evaluation suite (Sprint B-B)."""

import json

import pytest

from benchmarks.canonical.baselines import (
    compare,
    load_baselines,
    save_baselines,
)
from benchmarks.canonical.runner import run_all, run_scenario
from benchmarks.canonical.scenarios import (
    REQUIRED_SCENARIO_IDS,
    SCENARIO_SUITE_VERSION,
)


@pytest.fixture(scope="module")
def all_records():
    return run_all()


class TestScenarioSuite:
    def test_all_required_scenarios_present(self):
        assert len(REQUIRED_SCENARIO_IDS) == 8
        expected = {
            "normal_operation",
            "partial_observation_dropout",
            "conflicting_sensor_observations",
            "low_resource_condition",
            "safety_gate_rejection",
            "human_rejection",
            "human_override",
            "deterministic_replay",
        }
        assert set(REQUIRED_SCENARIO_IDS) == expected

    def test_every_scenario_completes_without_failures(self, all_records):
        for record in all_records:
            assert record["failures"] == [], record["scenario_id"]
            assert record["metrics"]["steps"] > 0

    def test_records_capture_required_data(self, all_records):
        for record in all_records:
            assert record["scenario_suite_version"] == SCENARIO_SUITE_VERSION
            for step in record["steps"]:
                # observations + world estimate + plans + safety + human + outcome
                assert "observation" in step
                assert "world_estimate" in step
                assert "candidate_plan_ids" in step
                assert "proposed_orders" in step
                assert "safety_verdict" in step
                assert step["human_state"] is not None
                assert "reward" in step
                assert "latency_ms" in step  # latency/compute metrics recorded
            m = record["metrics"]
            for key in ("candidates_evaluated", "feeds_generated", "feeds_received"):
                assert key in m
            # audit chain verified end-to-end for every scenario
            assert record["audit_chain_verified"] is True

    def test_safety_gate_rejection_produces_only_noops(self, all_records):
        rec = next(r for r in all_records if r["scenario_id"] == "safety_gate_rejection")
        assert rec["metrics"]["noop_steps"] == rec["metrics"]["steps"]
        assert rec["metrics"]["safety_rejections"] == rec["metrics"]["steps"]

    def test_human_rejection_never_executes(self, all_records):
        rec = next(r for r in all_records if r["scenario_id"] == "human_rejection")
        assert rec["metrics"]["human_rejections"] == rec["metrics"]["steps"]
        assert rec["metrics"]["total_reward"] == 0.0  # nothing executed
        assert all(s["executed_action"] is None for s in rec["steps"])

    def test_human_override_recorded(self, all_records):
        rec = next(r for r in all_records if r["scenario_id"] == "human_override")
        assert rec["metrics"]["overrides"] >= 1
        states = [s["human_state"] for s in rec["steps"]]
        assert any(str(s).startswith("OVERRIDDEN") for s in states)

    def test_deterministic_replay_fingerprints_match(self, all_records):
        rec = next(r for r in all_records if r["scenario_id"] == "deterministic_replay")
        assert rec["replay_matches"] is True
        assert rec["fingerprint"] == rec["replay_fingerprint"]



class TestDeterminism:
    def test_same_seed_same_fingerprint(self):
        from benchmarks.canonical.scenarios import SCENARIOS

        spec = SCENARIOS["normal_operation"]
        r1 = run_scenario(spec)
        r2 = run_scenario(spec)
        assert r1["fingerprint"] == r2["fingerprint"]

    def test_different_seed_usually_different_content(self):
        from benchmarks.canonical.scenarios import ScenarioSpec

        fingerprints = set()
        for seed in (1, 2, 3):
            rec = run_scenario(ScenarioSpec(
                scenario_id=f"seed_check_{seed}", description="",
                seed=seed, n_steps=4,
            ))
            fingerprints.add(rec["fingerprint"])
        assert len(fingerprints) >= 2


class TestBaselineGate:
    def test_green_against_committed_baselines(self, all_records):
        violations = compare(all_records, load_baselines())
        assert violations == []

    def test_detects_metric_regression(self, all_records):
        baselines = load_baselines()
        sid = all_records[0]["scenario_id"]
        baselines["scenarios"][sid]["metrics"]["total_reward"] += 100.0
        violations = compare(all_records, baselines)
        assert any("total_reward" in v for v in violations)

    def test_detects_fingerprint_change(self, all_records):
        baselines = load_baselines()
        sid = all_records[0]["scenario_id"]
        baselines["scenarios"][sid]["fingerprint"] = "deadbeef"
        violations = compare(all_records, baselines)
        assert any("fingerprint changed" in v for v in violations)

    def test_detects_missing_baseline(self, all_records, tmp_path):
        path = tmp_path / "b.json"
        save_baselines(all_records, path)
        loaded = load_baselines(path)
        del loaded["scenarios"]["normal_operation"]  # base still non-empty
        violations = compare(all_records, loaded)
        assert any("missing baselines" in v for v in violations)

    def test_detects_suite_version_change(self, all_records):
        baselines = load_baselines()
        baselines["scenario_suite_version"] = "ancient-v0"
        violations = compare(all_records, baselines)
        assert any("suite version changed" in v for v in violations)

    def test_replay_mismatch_is_a_violation(self, all_records):
        broken = [dict(r) for r in all_records]
        for r in broken:
            if r["scenario_id"] == "deterministic_replay":
                r["replay_matches"] = False
        violations = compare(broken, load_baselines())
        assert any("replay fingerprint mismatch" in v for v in violations)

    def test_baseline_file_round_trip(self, tmp_path, all_records):
        path = tmp_path / "baselines.json"
        save_baselines(all_records, path)
        data = json.loads(path.read_text(encoding="utf-8"))
        assert data["scenario_suite_version"] == SCENARIO_SUITE_VERSION
        assert set(data["scenarios"].keys()) == set(REQUIRED_SCENARIO_IDS)
        for entry in data["scenarios"].values():
            assert "fingerprint" in entry



class TestResearchDbSink:
    """Sprint B-D: research_db as long-term experiment-metadata catalog."""

    def test_benchmark_metadata_round_trips_through_research_db(
        self, all_records, tmp_path,
    ):
        from benchmarks.canonical.research_sink import (
            persist_run_metadata,
            record_to_benchmark_record,
        )

        ids = persist_run_metadata(all_records[:2], base_dir=tmp_path)
        assert len(ids) == 2

        from research_db.store import JSONResearchStore

        store = JSONResearchStore(base_dir=str(tmp_path))
        saved = store.get("benchmark", ids[0])
        assert saved is not None
        assert saved.name == f"canonical:{all_records[0]['scenario_id']}"
        assert saved.metrics["steps"] == all_records[0]["metrics"]["steps"]
        # provenance fields preserved for reproducibility
        env = saved.environment
        assert env["seed"] == all_records[0]["config"]["seed"]
        assert saved.baseline_results["fingerprint"] == all_records[0]["fingerprint"]

    def test_decision_audit_store_untouched_by_sink(self, tmp_path):
        from ultrone_hitl.audit_store import JSONLAuditStore
        from ultrone_hitl.pipeline_bridge import HITLBridge
        from core.contracts import DecisionTrace
        from benchmarks.canonical.research_sink import persist_run_metadata

        audit_path = tmp_path / "audit.jsonl"
        store = JSONLAuditStore(audit_path)
        trace = DecisionTrace(decision_id="DEC-x", episode_id="EP-1", tick=1)
        bridge = HITLBridge(store=store)
        bridge.submit_trace(trace, scenario_id="s")
        before = len(store.replay())

        persist_run_metadata(
            [{"scenario_id": "s", "config": {}, "metrics": {}}],
            base_dir=tmp_path / "rdb",
        )
        # The decision log is completely unaffected.
        assert len(store.replay()) == before
        assert store.verify() is True
