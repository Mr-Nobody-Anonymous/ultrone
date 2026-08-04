#!/usr/bin/env python3
"""Tests for the Benchmark Zoo."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
import unittest
from benchmarks.base import Benchmark, BenchmarkConfig, BenchmarkResult
from benchmarks.registry import BenchmarkRegistry

class TestBenchmark(unittest.TestCase):
    def test_config(self):
        c = BenchmarkConfig(name="test", num_episodes=5)
        self.assertEqual(c.name, "test")
    def test_evaluate(self):
        b = Benchmark(BenchmarkConfig(name="test", num_episodes=5))
        result = b.evaluate()
        self.assertEqual(result.episodes_completed, 5)
        self.assertGreaterEqual(result.mean_score, 0.0)

class TestBenchmarkRegistry(unittest.TestCase):
    def test_register_and_create(self):
        r = BenchmarkRegistry()
        r.register("test", Benchmark)
        b = r.create("test")
        self.assertIsInstance(b, Benchmark)
        self.assertEqual(r.count(), 1)

if __name__ == "__main__":
    unittest.main(verbosity=2)
