#!/usr/bin/env python3
"""Tests for AI Model Lifecycle (Phase 1)."""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import unittest

from brain.models.registry import ModelRegistry, ModelEntry
from brain.models.model_version import ModelVersion
from brain.models.checkpoint_manager import CheckpointManager, Checkpoint
from brain.models.model_manager import ModelManager, TrainingConfig
from brain.models.quantization import QuantizationManager, QuantizationConfig
from brain.models.distillation import DistillationManager, DistillationConfig
from brain.models.pruning import PruningManager, PruningConfig
from brain.models.exporter import ModelExporter, ExportConfig
from brain.models.converter import ModelConverter
from brain.models.rollback import ModelRollback


class TestModelVersion(unittest.TestCase):
    def test_parse_and_bump(self):
        v = ModelVersion.parse("1.2.3")
        self.assertEqual(str(v), "1.2.3")
        self.assertEqual(str(v.bump_minor()), "1.3.0")
        self.assertEqual(str(v.bump_major()), "2.0.0")
        self.assertEqual(str(v.bump_patch()), "1.2.4")

    def test_comparison(self):
        a = ModelVersion.parse("1.0.0")
        b = ModelVersion.parse("2.0.0")
        self.assertTrue(a < b)
        self.assertTrue(a.is_compatible_with(b) is False)


class TestModelRegistry(unittest.TestCase):
    def setUp(self):
        self.reg = ModelRegistry()

    def test_register_and_get(self):
        entry = ModelEntry(name="model_a", architecture="mlp")
        self.reg.register(entry)
        self.assertEqual(self.reg.get(entry.model_id).name, "model_a")

    def test_compare(self):
        a = ModelEntry(name="a", metrics={"accuracy": 0.9})
        b = ModelEntry(name="b", metrics={"accuracy": 0.95})
        self.reg.register(a)
        self.reg.register(b)
        comp = self.reg.compare(a.model_id, b.model_id)
        self.assertIn("metrics", comp)
        self.assertAlmostEqual(comp["metrics"]["accuracy"]["improvement"], 0.05 / 0.9, places=6)


class TestCheckpointManager(unittest.TestCase):
    def test_save_and_get_best(self):
        mgr = CheckpointManager()
        mgr.save("m1", epoch=1, step=0, metrics={"accuracy": 0.8})
        mgr.save("m1", epoch=2, step=0, metrics={"accuracy": 0.9})
        best = mgr.get_best("m1", metric="accuracy")
        self.assertEqual(best.metrics["accuracy"], 0.9)


class TestModelManager(unittest.TestCase):
    def test_registration_and_lifecycle(self):
        mgr = ModelManager()
        entry = mgr.register_model("test_model", "mlp")
        mgr.load(entry.model_id, model_obj=object())

        def train_fn(model, config):
            return {"accuracy": 0.92, "loss": 0.1}

        metrics = mgr.train(entry.model_id, train_fn, TrainingConfig(epochs=1))
        self.assertGreater(metrics["accuracy"], 0.5)
        self.assertEqual(mgr.registry.get(entry.model_id).status, "trained")

    def test_lora_adapter(self):
        mgr = ModelManager()
        entry = mgr.register_model("lora_model", "transformer")
        adapter = mgr.create_lora_adapter(entry.model_id, rank=4, alpha=8)
        self.assertEqual(adapter["rank"], 4)
        self.assertEqual(adapter["model_id"], entry.model_id)


class TestQuantizationManager(unittest.TestCase):
    def test_quantize(self):
        q = QuantizationManager()
        result = q.quantize({"params": 1}, QuantizationConfig(scheme="int8"), model_id="m1")
        self.assertEqual(result["scheme"], "int8")
        self.assertGreaterEqual(result["size_reduction_ratio"], 1.0)

    def test_invalid_scheme(self):
        q = QuantizationManager()
        with self.assertRaises(ValueError):
            q.quantize({}, QuantizationConfig(scheme="fp64"))


class TestDistillationManager(unittest.TestCase):
    def test_distill(self):
        dm = DistillationManager()
        teacher = {"name": "teacher"}
        student = {"name": "student"}
        result = dm.distill(teacher, student, DistillationConfig())
        self.assertIn("teacher_agreement", result["metrics"])
        self.assertGreaterEqual(result["metrics"]["teacher_agreement"], 0.0)


class TestPruningManager(unittest.TestCase):
    def test_prune(self):
        pm = PruningManager()
        result = pm.prune({"params": 1}, PruningConfig(amount=0.3), model_id="m1")
        self.assertEqual(result["amount"], 0.3)
        self.assertGreaterEqual(result["params_removed_ratio"], 0.0)

    def test_invalid_amount(self):
        pm = PruningManager()
        with self.assertRaises(ValueError):
            pm.prune({}, PruningConfig(amount=1.0))


class TestModelExporter(unittest.TestCase):
    def test_export(self):
        exporter = ModelExporter()
        result = exporter.export({"params": 1}, ExportConfig(format="onnx"), model_id="m1")
        self.assertEqual(result["format"], "onnx")
        self.assertIn("path", result)

    def test_invalid_format(self):
        exporter = ModelExporter()
        with self.assertRaises(ValueError):
            exporter.export({}, ExportConfig(format="unknown"))


class TestModelConverter(unittest.TestCase):
    def test_convert(self):
        conv = ModelConverter()
        result = conv.convert({"params": 1}, target="fp16", model_id="m1")
        self.assertEqual(result["target"], "fp16")

    def test_invalid_target(self):
        conv = ModelConverter()
        with self.assertRaises(ValueError):
            conv.convert({}, target="unknown")


class TestModelRollback(unittest.TestCase):
    def test_snapshot_and_rollback(self):
        reg = ModelRegistry()
        entry = ModelEntry(name="m1")
        reg.register(entry)
        rb = ModelRollback(reg)
        rb.snapshot(entry.model_id, {"accuracy": 0.95})
        record = rb.rollback(entry.model_id, reason="test")
        self.assertIsNotNone(record)
        self.assertEqual(reg.get(entry.model_id).status, "rolled_back")

    def test_no_history(self):
        rb = ModelRollback()
        self.assertIsNone(rb.rollback("nonexistent"))


if __name__ == "__main__":
    unittest.main(verbosity=2)


