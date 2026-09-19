"""Tests for Scientific Benchmarking Framework and Evidence-Backed Governance."""

import pytest
from packages.research.benchmarking.metrics import (
    calculate_brier_score,
    calculate_expected_calibration_error,
    calculate_task_accuracy,
)
from packages.research.benchmarking.runner import BenchmarkSuiteRunner
from packages.research.benchmarking.statistics import compute_paired_statistics
from packages.runtime.governance.capabilities import CapabilityEntry, CapabilityRegistry


def test_scientific_metrics_computation():
    # Accuracy
    acc = calculate_task_accuracy(["a", "b", "c", "d"], ["a", "b", "c", "x"])
    assert acc == 0.75

    # Brier Score (MSE of probabilistic forecasts)
    # Perfect predictions have Brier score = 0.0
    perfect_brier = calculate_brier_score([1.0, 0.0], [1, 0])
    assert perfect_brier == 0.0
    # Uncertain coin flips (0.5 on binary) have Brier score = 0.25
    uncertain_brier = calculate_brier_score([0.5, 0.5], [1, 0])
    assert uncertain_brier == 0.25

    # Expected Calibration Error (ECE)
    ece = calculate_expected_calibration_error([0.9, 0.8, 0.2, 0.1], [1, 1, 0, 0], n_bins=5)
    assert 0.0 <= ece <= 0.2


def test_paired_statistics_confidence_interval_and_effect_size():
    # Candidate consistently outperforms baseline across 5 random seeds
    baseline = [0.70, 0.72, 0.69, 0.71, 0.68]
    candidate = [0.85, 0.88, 0.84, 0.86, 0.83]

    stats = compute_paired_statistics(baseline, candidate)
    assert stats.n_samples == 5
    assert stats.delta_mean > 0.14
    # 95% CI lower bound must be strictly positive
    assert stats.ci_lower_95 > 0.10
    # Large positive Cohen's d
    assert stats.cohens_d > 2.0
    assert stats.is_significant is True


def test_benchmark_suite_runner():
    runner = BenchmarkSuiteRunner(seeds=[10, 20, 30])
    res = runner.evaluate_candidate_vs_baseline(
        task_name="waypoint_evasion_benchmark",
        baseline_eval_fn=lambda seed: 0.60 + (seed % 5) * 0.01,
        candidate_eval_fn=lambda seed: 0.80 + (seed % 5) * 0.01,
    )
    assert res["task_name"] == "waypoint_evasion_benchmark"
    assert res["promotion_eligible"] is True
    assert "ci_95" in res["statistics"]
    assert len(res["raw_scores"]["baseline"]) == 3


def test_evidence_backed_maturity_level_calculation():
    # 1. Module without integration tests cannot exceed L2
    unit_only = CapabilityEntry(
        key="test_mod",
        name="Test",
        maturity_level="L4",  # Developer claimed L4
        status="active",
        unit_tests=True,
        integration_tests=False,
        benchmarked=False,
        reproducible=False,
        simulation_only=True,
        description="",
    )
    achievable = CapabilityRegistry.calculate_achievable_level(unit_only)
    assert achievable == "L2"  # Mechanically capped at L2

    # 2. Verify all repository capabilities against active evidence
    reg = CapabilityRegistry()
    report = reg.verify_evidence()
    assert len(report) >= 10
    # Ensure no declared capability exceeds achievable evidence
    for k, v in report.items():
        assert v["is_valid"] is True, f"Capability '{k}' declared {v['declared_level']} but evidence only supports {v['achievable_level']}"


def test_bootstrap_ci_computation():
    """Verify bootstrap confidence interval computation over paired differences."""
    from packages.research.benchmarking.statistics import compute_bootstrap_ci

    diffs = [0.15, 0.16, 0.14, 0.15, 0.17, 0.15, 0.16, 0.14]
    ci_lower, ci_upper = compute_bootstrap_ci(diffs, n_resamples=500, confidence_level=0.95)
    assert 0.13 <= ci_lower <= 0.16
    assert 0.14 <= ci_upper <= 0.17
    assert ci_lower < ci_upper


def test_benchmark_contamination_guard():
    """Verify that training data or candidate artifacts containing holdout data are rejected."""
    from packages.research.benchmarking.contamination import ContaminationGuard, DatasetManifest, DatasetSplit

    holdout_samples = [
        "target_coords: 34.05, -118.24; adversary_doctrine: alpha_swarm",
        "target_coords: 51.50, -0.12; adversary_doctrine: beta_radar",
    ]
    manifest = DatasetManifest.create(DatasetSplit.HOLDOUT, holdout_samples)
    guard = ContaminationGuard([manifest])

    # Clean candidate
    clean_training = ["target_coords: 40.71, -74.00; doctrine: gamma_patrol"]
    clean_ok, err = guard.inspect_training_data(clean_training)
    assert clean_ok is True
    assert err is None

    # Contaminated candidate containing exact holdout sample
    contaminated_training = [
        "target_coords: 40.71, -74.00; doctrine: gamma_patrol",
        "target_coords: 34.05, -118.24; adversary_doctrine: alpha_swarm",  # Leakage!
    ]
    contam_ok, contam_err = guard.inspect_training_data(contaminated_training)
    assert contam_ok is False
    assert "contamination detected" in contam_err
