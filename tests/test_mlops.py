#!/usr/bin/env python3
"""Tests for MLOps (Phase 3)."""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import unittest
from mlops.experiment_tracker import ExperimentTracker
from mlops.model_registry import MLOpsModelRegistry
from mlops.deployment import DeploymentManager
from mlops.monitoring import MonitoringService
from mlops.drift_detection import DriftDetector
from mlops.feature_store import FeatureStore
from mlops.lineage import LineageTracker
from mlops.artifact_store import ArtifactStore


class TestExperimentTracker(unittest.TestCase):
    def setUp(self):
        self.tracker = ExperimentTracker()

    def test_start_run(self):
        run_id = self.tracker.start_run(name="test", params={"lr": 0.01})
        self.assertIsNotNone(run_id)

    def test_log_metric_and_end(self):
        self.tracker.start_run()
        self.tracker.log_metric("accuracy", 0.95)
        self.tracker.end_run()
        run = self.tracker.list_runs()[0]
        self.assertEqual(run.metrics["accuracy"], 0.95)
        self.assertEqual(run.status, "completed")

    def test_get_best(self):
        self.tracker.start_run("a")
        self.tracker.log_metric("accuracy", 0.8)
        self.tracker.end_run()
        self.tracker.start_run("b")
        self.tracker.log_metric("accuracy", 0.9)
        self.tracker.end_run()
        best = self.tracker.get_best("accuracy")
        self.assertEqual(best.name, "b")


class TestMLOpsModelRegistry(unittest.TestCase):
    def setUp(self):
        self.reg = MLOpsModelRegistry()

    def test_register_and_transition(self):
        model = self.reg.register("model_a", version="1.0.0")
        self.assertTrue(self.reg.transition(model.model_id, "production"))
        self.assertEqual(self.reg.get(model.model_id).stage, "production")

    def test_get_production(self):
        m = self.reg.register("model_a")
        self.reg.transition(m.model_id, "production")
        self.assertEqual(self.reg.get_production("model_a").model_id, m.model_id)


class TestDeploymentManager(unittest.TestCase):
    def setUp(self):
        self.mgr = DeploymentManager()

    def test_deploy(self):
        dep = self.mgr.deploy("model_1", "http://localhost:8000")
        self.assertEqual(dep.status, "live")
        self.assertEqual(len(self.mgr.list_deployments()), 1)

    def test_stop(self):
        dep = self.mgr.deploy("model_1", "http://localhost:8000")
        self.assertTrue(self.mgr.stop(dep.deployment_id))
        self.assertEqual(self.mgr.get_deployment(dep.deployment_id).status, "stopped")


class TestMonitoringService(unittest.TestCase):
    def setUp(self):
        self.mon = MonitoringService()

    def test_record_and_health(self):
        self.mon.record("model_1", latency_ms=100, error=False)
        health = self.mon.get_health("model_1")
        self.assertEqual(health["status"], "healthy")

    def test_alert(self):
        for _ in range(20):
            self.mon.record("model_1", latency_ms=10, error=True)
        alerts = self.mon.get_alerts("model_1")
        self.assertTrue(any(a["type"] == "high_error_rate" for a in alerts))


class TestDriftDetector(unittest.TestCase):
    def setUp(self):
        self.det = DriftDetector()

    def test_no_drift(self):
        ref = {"f": [1.0, 2.0, 3.0, 4.0, 5.0]}
        cur = {"f": [1.1, 2.1, 3.1, 4.1, 5.1]}
        self.det.set_reference(ref)
        report = self.det.check(cur)
        self.assertIn("drifted", report)

    def test_drift(self):
        ref = {"f": [1.0, 2.0, 3.0, 4.0, 5.0]}
        cur = {"f": [50.0, 60.0, 70.0, 80.0, 90.0]}
        self.det.set_reference(ref)
        report = self.det.check(cur)
        self.assertEqual(report["drifted"], True)


class TestFeatureStore(unittest.TestCase):
    def setUp(self):
        self.store = FeatureStore()

    def test_register_and_get(self):
        self.store.register_feature("age", dtype="int")
        feature = self.store.get_feature_by_name("age")
        self.assertIsNotNone(feature)
        self.assertEqual(feature.dtype, "int")

    def test_log_values(self):
        self.store.log_values("age", [1, 2, 3])
        stats = self.store.get_stats()
        self.assertEqual(stats["features_with_values"], 1)


class TestLineageTracker(unittest.TestCase):
    def setUp(self):
        self.tracker = LineageTracker()

    def test_add_and_provenance(self):
        ds = self.tracker.add_node("dataset", "ds1")
        model = self.tracker.add_node("model", "model1", parents=[ds.node_id])
        chain = self.tracker.get_provenance(model.node_id)
        self.assertEqual(len(chain), 2)


class TestArtifactStore(unittest.TestCase):
    def setUp(self):
        self.store = ArtifactStore(base_dir="tests/test_artifacts")

    def test_store_bytes(self):
        art = self.store.store("model.bin", "model", data=b"hello")
        self.assertEqual(art.size_bytes, 5)
        self.assertEqual(self.store.get(art.artifact_id).name, "model.bin")

    def test_get_by_name(self):
        self.store.store("model.bin", "model", data=b"data")
        arts = self.store.get_by_name("model.bin")
        self.assertEqual(len(arts), 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
