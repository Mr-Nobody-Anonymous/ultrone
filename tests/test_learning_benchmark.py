# Copyright (c) Ultrone Contributors. All rights reserved.
"""Tests for the measurable closed-loop learning benchmark.

A learning loop is only proven if:
- the training-set score genuinely improves across cycles;
- the improvement transfers to *unseen* scenarios (generalization);
- no previously solved scenario regresses;
- repeated runs are bit-reproducible;
- the promoted configuration lands in the production brain channel.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

from adaptive.optimizer import config_hash
from adaptive.promotion import BrainStore
from benchmarks.learning_benchmark import (
    REGRESSION_TOLERANCE,
    BenchmarkReport,
    LearningBenchmark,
)

_EXPECTED_ITERATIONS = 6   # LearningBenchmark defaults


def test_benchmark_improves_and_generalizes(tmp_path: Path):
    """The headline: real learning measured on unseen worlds."""
    report = LearningBenchmark(
        storage_dir=str(tmp_path / "brain")).run()

    # -- structure -------------------------------------------------------- #
    assert len(report.iterations) == _EXPECTED_ITERATIONS
    assert report.learning_curve_monotone, (
        "best-so-far learning curve must be non-decreasing:\n"
        f"{[r.train_score for r in report.iterations]}")

    # -- measurable learning on the TRAINING set -------------------------- #
    assert report.final_train_mean > report.baseline_train_mean, (
        f"no aggregate training improvement:\n{report.to_table()}")
    for name, base in report.baseline_train_scores.items():
        final = report.final_train_scores[name]
        assert final >= base - REGRESSION_TOLERANCE, (
            f"training scenario {name} regressed: {base} -> {final}")

    # -- generalization to UNSEEN scenarios -------------------------------- #
    assert report.final_holdout_mean > report.baseline_holdout_mean, (
        f"adaptation did not transfer to unseen scenarios:\n"
        f"{report.to_table()}")
    for name, base in report.baseline_holdout_scores.items():
        final = report.final_holdout_scores[name]
        assert final >= base - REGRESSION_TOLERANCE, (
            f"unseen scenario {name} got worse: {base} -> {final}")

    # -- governance verdicts ----------------------------------------------- #
    assert report.reproducibility_passed, (
        f"results not reproducible:\n{report.to_table()}")
    assert report.regression_suite_passed, report.regression_failures
    assert report.promoted, (
        f"expected promotion, decision={report.decision!r}: "
        f"{report.reason}")

    # -- the loop closes in the brain store, not just in memory ------------ #
    store = BrainStore(storage_dir=str(tmp_path / "brain"))
    store.load()
    production_hash = config_hash(store.get_config("production"))
    assert production_hash == report.config_hash, (
        "production channel does not hold the promoted configuration")


def test_benchmark_rejects_overlapping_seed_sets():
    """'Unseen' is meaningless if seeds leak between train and holdout."""
    with pytest.raises(ValueError):
        LearningBenchmark(train_seeds=(1, 2, 3), holdout_seeds=(3, 4))


def test_report_serializes_to_json(tmp_path: Path):
    """Machine-readable reports persist and round-trip losslessly."""
    report = LearningBenchmark(
        iterations=2, population_size=4, generations_per_iteration=1,
        train_seeds=(101,), holdout_seeds=(202,)).run()
    out_path = tmp_path / "reports" / "learning.json"
    report.save_json(out_path)

    payload = json.loads(out_path.read_text(encoding="utf-8"))
    restored = BenchmarkReport(
        train_seeds=tuple(payload["train_seeds"]),
        holdout_seeds=tuple(payload["holdout_seeds"]),
    )
    assert payload["train_seeds"] == list(report.train_seeds)
    assert payload["baseline_train_mean"] == report.baseline_train_mean
    assert payload["config_hash"] == report.config_hash
    assert payload["promoted"] == report.promoted
    assert isinstance(payload["learning_curve_monotone"], bool)
    assert restored.train_seeds == report.train_seeds


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))