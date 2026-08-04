#!/usr/bin/env python3
"""Tests for the AutoML package."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
import unittest
from automl.nas import NeuralArchitectureSearch
from automl.auto_tuner import AutoTuner
from automl.auto_ensemble import AutoEnsemble

class TestNAS(unittest.TestCase):
    def test_sample(self):
        nas = NeuralArchitectureSearch()
        arch = nas.sample()
        self.assertGreater(len(arch.layers), 0)
        self.assertEqual(nas.candidate_count, 1)

class TestAutoTuner(unittest.TestCase):
    def test_suggest(self):
        tuner = AutoTuner()
        space = {"lr": [0.001, 0.01, 0.1], "batch": [32, 64]}
        config = tuner.suggest(space)
        self.assertIn("lr", config)
        self.assertEqual(tuner.trial_count, 1)

class TestAutoEnsemble(unittest.TestCase):
    def test_add_and_predict(self):
        ens = AutoEnsemble()
        ens.add_model("model1")
        self.assertEqual(ens.model_count, 1)
        result = ens.predict(None)
        self.assertIsNotNone(result)

if __name__ == "__main__":
    unittest.main(verbosity=2)
