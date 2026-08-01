#!/usr/bin/env python3
"""Tests for Prediction models (Phase 8)."""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import unittest
import numpy as np
from brain.learning.prediction.base import SequencePredictor, PredictionConfig, PredictionResult
from brain.learning.prediction.lstm import LSTMPredictor, LSTMConfig
from brain.learning.prediction.gru import GRUPredictor, GRUConfig
from brain.learning.prediction.transformer import TransformerPredictor, TransformerConfig
from brain.learning.prediction.trajectory import TrajectoryPredictor, TrajectoryConfig
from brain.learning.prediction.change_point import ChangePointDetector, ChangePointConfig


class TestPredictionInterface(unittest.TestCase):
    def test_base_instantiation_fails(self):
        with self.assertRaises(TypeError):
            SequencePredictor(PredictionConfig())

    def test_lstm_implements_interface(self):
        p = LSTMPredictor()
        self.assertIsInstance(p, SequencePredictor)

    def test_gru_implements_interface(self):
        p = GRUPredictor()
        self.assertIsInstance(p, SequencePredictor)

    def test_transformer_implements_interface(self):
        p = TransformerPredictor()
        self.assertIsInstance(p, SequencePredictor)

    def test_trajectory_implements_interface(self):
        p = TrajectoryPredictor()
        self.assertIsInstance(p, SequencePredictor)

    def test_change_point_implements_interface(self):
        p = ChangePointDetector()
        self.assertIsInstance(p, SequencePredictor)


class TestLSTMPredictor(unittest.TestCase):
    def setUp(self):
        self.model = LSTMPredictor(LSTMConfig(input_window=10, hidden_dim=16))

    def test_predict(self):
        x = np.random.randn(10, 5)
        result = self.model.predict(x)
        self.assertIsInstance(result, PredictionResult)

    def test_get_stats(self):
        stats = self.model.get_stats()
        self.assertIn("type", stats)


class TestGRUPredictor(unittest.TestCase):
    def setUp(self):
        self.model = GRUPredictor(GRUConfig(input_window=10, hidden_dim=16))

    def test_predict(self):
        x = np.random.randn(10, 5)
        result = self.model.predict(x)
        self.assertIsInstance(result, PredictionResult)


class TestTransformerPredictor(unittest.TestCase):
    def setUp(self):
        self.model = TransformerPredictor(TransformerConfig(input_window=10, hidden_dim=16))

    def test_predict(self):
        x = np.random.randn(10, 5)
        result = self.model.predict(x)
        self.assertIsInstance(result, PredictionResult)


class TestTrajectoryPredictor(unittest.TestCase):
    def setUp(self):
        self.model = TrajectoryPredictor()

    def test_predict(self):
        x = np.random.randn(10, 3)
        result = self.model.predict(x)
        self.assertIsInstance(result, PredictionResult)


class TestChangePointDetector(unittest.TestCase):
    def setUp(self):
        self.model = ChangePointDetector()

    def test_detect(self):
        x = np.random.randn(100)
        result = self.model.predict(x)
        self.assertIsInstance(result, PredictionResult)


class TestPredictionResult(unittest.TestCase):
    def test_mean_prediction_property(self):
        result = PredictionResult(predictions=np.array([[1, 2], [3, 4]]))
        self.assertEqual(result.mean_prediction.tolist(), [2.0, 3.0])

    def test_mean_prediction_1d(self):
        result = PredictionResult(predictions=np.array([1, 2, 3]))
        self.assertEqual(result.mean_prediction.tolist(), [1, 2, 3])


if __name__ == "__main__":
    unittest.main(verbosity=2)

