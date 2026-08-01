#!/usr/bin/env python3
"""Tests for Probabilistic Reasoning (Phase 5)."""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import unittest
import numpy as np
from brain.perception.probabilistic.bayesian_network import BayesianNetwork, BayesianNetworkConfig
from brain.perception.probabilistic.hidden_markov import HiddenMarkovModel, HMMConfig
from brain.perception.probabilistic.kalman_filter import KalmanFilter, KFConfig, ExtendedKalmanFilter, UnscentedKalmanFilter
from brain.perception.probabilistic.particle_filter import ParticleFilter, ParticleFilterConfig
from brain.perception.probabilistic.belief_propagation import BeliefPropagation, BPConfig


class TestBayesianNetwork(unittest.TestCase):
    def setUp(self):
        self.bn = BayesianNetwork()

    def test_add_node(self):
        self.bn.add_node("A", states=["True", "False"])
        self.assertIn("A", self.bn._nodes)

    def test_get_stats(self):
        stats = self.bn.get_stats()
        self.assertIn("num_nodes", stats)


class TestHiddenMarkovModel(unittest.TestCase):
    def setUp(self):
        self.hmm = HiddenMarkovModel()

    def test_get_stats(self):
        stats = self.hmm.get_stats()
        self.assertIn("num_states", stats)


class TestKalmanFilter(unittest.TestCase):
    def setUp(self):
        self.kf = KalmanFilter()

    def test_predict(self):
        result = self.kf.predict(step=1)
        self.assertIsNotNone(result)


class TestExtendedKalmanFilter(unittest.TestCase):
    def setUp(self):
        self.ekf = ExtendedKalmanFilter()

    def test_predict(self):
        result = self.ekf.predict(step=1)
        self.assertIsNotNone(result)


class TestUnscentedKalmanFilter(unittest.TestCase):
    def setUp(self):
        self.ukf = UnscentedKalmanFilter()

    def test_predict(self):
        result = self.ukf.predict(step=1)
        self.assertIsNotNone(result)


class TestParticleFilter(unittest.TestCase):
    def setUp(self):
        self.pf = ParticleFilter()

    def test_predict(self):
        result = self.pf.predict(step=1)
        self.assertIsNotNone(result)


class TestBeliefPropagation(unittest.TestCase):
    def setUp(self):
        self.bp = BeliefPropagation()

    def test_get_stats(self):
        stats = self.bp.get_stats()
        self.assertIn("num_nodes", stats)


if __name__ == "__main__":
    unittest.main(verbosity=2)

