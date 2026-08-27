# Copyright (c) Ultrone Contributors. All rights reserved.
"""End-to-end tests: the optimizer evolves the ROUTING POLICY itself."""

from __future__ import annotations

import json

import pytest

from adaptive.optimizer import config_hash
from adaptive.promotion import BrainStore
from benchmarks.orchestration_benchmark import OrchestrationBenchmark


def test_routing_policy_evolution_generalizes_to_unseen_tasks(tmp_path):
    """The headline: evolved policy wins on training AND holdout tasks."""
    report = OrchestrationBenchmark(
        storage_dir=str(tmp_path / "brain")).run()

    # -- learning curve ---------------------------------------------------- #
    assert len(report.iterations) == 5
    assert report.learning_curve_monotone, (
        f"curve not monotone: "
        f"{[r.train_score for r in report.iterations]}")
    assert report.final_train_mean > report.baseline_train_mean, (
        f"no training improvement:\n{report.to_table()}")

    # -- generalization to tasks never seen by the optimizer ---------------- #
    # Holdout data *measures* transfer; it must never gate adaptation
    # (gating unseen tasks would quietly turn them into training data).
    # So: the AGGREGATE must strictly improve, individual dips stay
    # bounded, and the hard per-task guarantee lives in the regression
    # suite over training tasks (asserted via the report below).
    assert report.final_holdout_mean > report.baseline_holdout_mean, (
        f"policy did not transfer to unseen tasks:\n"
        f"{report.to_table()}")
    holdout_dips = [
        report.final_holdout_scores[name] - base
        for name, base in report.baseline_holdout_scores.items()]
    assert min(holdout_dips) > -0.35, (
        f"unbounded regression on unseen tasks: {holdout_dips}")

    # -- governance verdicts ------------------------------------------------- #
    assert report.regression_suite_passed, report.regression_failures
    assert report.reproducibility_passed, "replay disagreed with first run"
    assert report.promoted, (
        f"expected promotion, got {report.decision!r}: {report.reason}")

    # -- the promoted POLICY lands in production ---------------------------- #
    store = BrainStore(storage_dir=str(tmp_path / "brain"))
    store.load()
    production = store.get_config("production")
    assert config_hash(production) == report.config_hash


def test_promoted_policy_actually_moves_the_knobs(tmp_path):
    """Promotion without parameter movement would be theater."""
    bench = OrchestrationBenchmark(
        iterations=2, population_size=6, generations_per_iteration=2,
        train_seeds=(11, 23, 37), holdout_seeds=(7, 19),
        storage_dir=str(tmp_path / "brain"))
    report = bench.run()

    from orchestration.router import default_routing_registry
    baseline_cfg = default_routing_registry().snapshot()
    store = BrainStore(storage_dir=str(tmp_path / "brain"))
    store.load()
    production = store.get_config("production")

    moved = sum(1 for name, value in baseline_cfg.items()
                if abs(float(production.get(name, value))
                       - float(value)) > 1e-9)
    assert moved >= 1, (
        "promoted policy is byte-identical to defaults; nothing learned")


def test_promoted_policy_drives_the_next_run(tmp_path):
    """Sprint-B's headline assertion, orchestration edition.

    Rebuilding an Orchestrator from the BrainStore production channel
    must route under the promoted policy -- proven not by trusting the
    store, but by the stamp inside freshly produced traces::

        fresh_trace.configuration_hash == promoted.configuration_hash

    Without this half, 'the policy is in production' would stay an
    inert claim: stored JSON no executor ever reads back.
    """
    from orchestration.router import (
        Orchestrator,
        RoutingPolicy,
        default_routing_registry,
    )
    from orchestration.task_classifier import synthetic_profile
    from orchestration.traces import TraceLog

    report = OrchestrationBenchmark(
        storage_dir=str(tmp_path / "brain")).run()
    assert report.promoted, "precondition: benchmark must promote"

    store = BrainStore(storage_dir=str(tmp_path / "brain"))
    store.load()
    fresh_registry = default_routing_registry()
    fresh_registry.apply(store.get_config("production"))
    fresh_orchestrator = Orchestrator(RoutingPolicy(fresh_registry))

    log = TraceLog(tmp_path / "next_runs.jsonl")
    outcome = fresh_orchestrator.run(synthetic_profile(901),
                                     trace_log=log)
    fresh_traces = log.load()

    assert outcome.accepted
    # THE closure assertion.
    assert len(fresh_traces) == 1
    assert fresh_traces[0].configuration_hash == report.config_hash, (
        "fresh orchestrator did not route under the promoted policy; "
        "the orchestration loop is open")

    # Provenance sanity: a default-policy orchestrator stamps a
    # different hash, so the field truly discriminates policies.
    baseline_log = TraceLog(tmp_path / "baseline_runs.jsonl")
    Orchestrator(RoutingPolicy()).run(synthetic_profile(902),
                                      trace_log=baseline_log)
    assert (baseline_log.load()[0].configuration_hash
            != report.config_hash)


if __name__ == "__main__":
    import sys
    sys.exit(pytest.main([__file__, "-v"]))


def test_disjoint_seed_families_are_enforced():
    with pytest.raises(ValueError):
        OrchestrationBenchmark(train_seeds=(1, 2, 3),
                               holdout_seeds=(3, 4))


def test_report_persists_as_json(tmp_path):
    report = OrchestrationBenchmark(
        iterations=1, population_size=4, generations_per_iteration=1,
        train_seeds=(101,), holdout_seeds=(202,),
        storage_dir=None).run()
    out = tmp_path / "routing_report.json"
    report.save_json(out)
    payload = json.loads(out.read_text(encoding="utf-8"))
    assert payload["train_seeds"] == [101]
    assert payload["baseline_train_mean"] == report.baseline_train_mean


if __name__ == "__main__":
    import sys
    sys.exit(pytest.main([__file__, "-v"]))