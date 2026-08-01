#!/usr/bin/env python3
"""Tests for Research Tooling (Phase 14)."""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import unittest
import numpy as np
from research.experiment_manager import ExperimentManager, ExperimentConfig
from research.hyperparameter_optimizer import HyperparameterOptimizer, HPOConfig
from research.scenario_benchmark import ScenarioBenchmark, BenchmarkConfig
from research.reproducibility import ReproducibilityManager, ReproducibilityConfig
from research.statistical_evaluation import StatisticalEvaluator, EvalConfig
from research.ablation_framework import AblationFramework, AblationConfig
from research.automated_report import AutomatedReport, ReportConfig


class TestExperimentManager(unittest.TestCase):
    def setUp(self):
        self.mgr = ExperimentManager()

    def test_create_experiment(self):
        exp_id = self.mgr.create_experiment(name="test_exp", config={})
        self.assertIsNotNone(exp_id)

    def test_get_stats(self):
        stats = self.mgr.get_stats()
        self.assertIn("num_experiments", stats)


class TestHyperparameterOptimizer(unittest.TestCase):
    def setUp(self):
        self.opt = HyperparameterOptimizer()

    def test_optimize(self):
        def objective(params):
            return params.get("x", 0) ** 2

        param_space = {"x": [-5.0, 5.0]}
        result = self.opt.optimize(objective, param_space, n_trials=10)
        self.assertIsNotNone(result)

    def test_get_stats(self):
        stats = self.opt.get_stats()
        self.assertIn("best_score", stats)


class TestScenarioBenchmark(unittest.TestCase):
    def setUp(self):
        self.bench = ScenarioBenchmark()

    def test_run(self):
        results = self.bench.run(scenarios=["test_scenario"])
        self.assertIsNotNone(results)

    def test_compare(self):
        results_a = {"accuracy": 0.9}
        results_b = {"accuracy": 0.85}
        comparison = self.bench.compare(results_a, results_b)
        self.assertIsNotNone(comparison)


class TestReproducibility(unittest.TestCase):
    def setUp(self):
        self.repro = ReproducibilityManager()

    def test_snapshot_and_restore(self):
        snapshot_id = self.repro.snapshot(config={"param": 1})
        self.assertIsNotNone(snapshot_id)
        restore_snapshot = self.repro.restore(snapshot_id)
        self.assertIsNotNone(restore_snapshot)

    def test_get_stats(self):
        stats = self.repro.get_stats()
        self.assertIn("num_snapshots", stats)


class TestStatisticalEvaluator(unittest.TestCase):
    def setUp(self):
        self.eval = StatisticalEvaluator()

    def test_evaluate(self):
        results = np.random.randn(100)
        evaluation = self.eval.evaluate(results)
        self.assertIsNotNone(evaluation)

    def test_compare_groups(self):
        group_a = np.random.randn(50)
        group_b = np.random.randn(50) + 0.5
        comparison = self.eval.compare_groups(group_a, group_b)
        self.assertIsNotNone(comparison)


class TestAblationFramework(unittest.TestCase):
    def setUp(self):
        self.ablation = AblationFramework()

    def test_run_ablation(self):
        def objective(config):
            return config.get("value", 0)

        results = self.ablation.run(
            base_config={"value": 1.0},
            components=["value"],
            objective_fn=objective,
        )
        self.assertIsNotNone(results)

    def test_get_stats(self):
        stats = self.ablation.get_stats()
        self.assertIn("num_ablations", stats)


class TestAutomatedReport(unittest.TestCase):
    def setUp(self):
        self.report = AutomatedReport()

    def test_generate(self):
        data = {"accuracy": 0.95, "f1_score": 0.93}
        report = self.report.generate(data, title="Test Report")
        self.assertIsNotNone(report)

    def test_get_stats(self):
        stats = self.report.get_stats()
        self.assertIn("num_reports", stats)


if __name__ == "__main__":
    unittest.main(verbosity=2)

