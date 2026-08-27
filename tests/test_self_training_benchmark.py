# Copyright (c) Ultrone Contributors. All rights reserved.
"""Tests for multidimensional capability evaluation + the benchmark."""

from __future__ import annotations

import json

import pytest

from self_improvement.self_training.evaluation import (
    CapabilityComparison,
    compare_capabilities,
    evaluate_capabilities,
)
from self_improvement.self_training.regression import (
    RegressionSuite,
    build_families,
)
from self_improvement.self_training.trainer import LearnedWeights


def _weights(**values):
    defaults = {"reasoning": 0.5, "coding": 0.5,
                "retrieval": 0.5, "tool_use": 0.5}
    defaults.update(values)
    return LearnedWeights(values=defaults)


FAMILIES = build_families(n_each=3)


class TestCapabilityMetrics:
    def test_deterministic(self):
        weights = _weights(reasoning=0.7)
        a = evaluate_capabilities(weights, FAMILIES)
        b = evaluate_capabilities(weights, FAMILIES)
        assert a.to_dict() == b.to_dict()

    def test_reports_all_dimensions(self):
        metrics = evaluate_capabilities(_weights(), FAMILIES)
        fields = ("reasoning", "planning", "memory", "tool_use",
                  "generalization", "robustness",
                  "simulation_performance", "latency_ms",
                  "resource_cost")
        for field in fields:
            assert hasattr(metrics, field)


class TestCapabilityComparison:
    def test_stronger_candidate_is_measurably_better(self):
        base = _weights(reasoning=0.4)
        cand = _weights(reasoning=0.95)
        regression = RegressionSuite(families=FAMILIES).run(cand, base)
        cmp = compare_capabilities(base, cand, FAMILIES,
                                   regression=regression,
                                   reproducible=True)
        assert cmp.measurably_better
        assert cmp.overall and cmp.holdout_improvement \
            and cmp.reproducible and cmp.no_critical_regression
        assert set(cmp.deltas) >= {"reasoning", "generalization"}

    def test_weaker_candidate_is_rejected(self):
        base = _weights(reasoning=0.9)
        cand = _weights(reasoning=0.1)
        regression = RegressionSuite(families=FAMILIES).run(cand, base)
        cmp = compare_capabilities(base, cand, FAMILIES,
                                   regression=regression)
        assert not cmp.measurably_better
        assert (not cmp.overall) or (not cmp.no_critical_regression)


class TestBenchmark:
    def test_reports_measurable_improvement_and_persists(self, tmp_path):
        from benchmarks.self_training_benchmark import (
            SelfTrainingBenchmark,
        )
        bench = SelfTrainingBenchmark(
            workdir=str(tmp_path / "work"),
            starter=_weights(reasoning=0.62, coding=0.66,
                             retrieval=0.56, tool_use=0.68),
            cycles=3, batch=10, family_each=3)
        report = bench.run()

        assert report.promoted_any
        assert report.regression_passed
        # base -> final differs AND final measures better
        assert report.final_hash != report.baseline_hash
        assert report.measurably_better
        assert report.comparison["deltas"]["generalization"] > 0

        out = tmp_path / "st_report.json"
        report.save_json(out)
        payload = json.loads(out.read_text(encoding="utf-8"))
        assert payload["baseline_hash"] == report.baseline_hash
        assert payload["measurably_better"] is True