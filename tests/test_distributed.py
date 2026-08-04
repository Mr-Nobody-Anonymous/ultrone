#!/usr/bin/env python3
"""Tests for Distributed Learning."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
import unittest
import numpy as np
from brain.learning.distributed.federated import FederatedLearning
from brain.learning.distributed.parameter_server import ParameterServer

class TestFederatedLearning(unittest.TestCase):
    def test_aggregate(self):
        fl = FederatedLearning(num_clients=3)
        params = {"w": np.array([1.0, 2.0])}
        fl.initialize(params)
        client_params = [{"w": np.array([1.0, 2.0])}, {"w": np.array([3.0, 4.0])}]
        result = fl.aggregate(client_params)
        self.assertEqual(fl.round_number, 1)
        np.testing.assert_array_equal(result["w"], np.array([2.0, 3.0]))

class TestParameterServer(unittest.TestCase):
    def test_push_pull(self):
        ps = ParameterServer()
        ps.initialize({"w": np.array([1.0, 2.0])})
        params = ps.pull_params()
        np.testing.assert_array_equal(params["w"], np.array([1.0, 2.0]))
        ps.push_gradients({"w": np.array([0.1, 0.2])})
        self.assertEqual(ps.pending_gradients, 1)
        ps.apply_gradients(lr=0.1)
        self.assertEqual(ps.pending_gradients, 0)

if __name__ == "__main__":
    unittest.main(verbosity=2)
