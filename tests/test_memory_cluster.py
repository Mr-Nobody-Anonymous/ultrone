#!/usr/bin/env python3
"""Tests for the Memory Cluster package."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
import unittest
from memory_cluster.redis_backend import RedisBackend
from memory_cluster.duckdb_backend import DuckDBBackend
from memory_cluster.base import ClusterRegistry

class TestRedisBackend(unittest.TestCase):
    def test_put_get(self):
        backend = RedisBackend()
        self.assertTrue(backend.connect())
        self.assertTrue(backend.put("key1", "value1"))
        self.assertEqual(backend.get("key1"), "value1")
        self.assertTrue(backend.delete("key1"))
        self.assertIsNone(backend.get("key1"))

class TestDuckDBBackend(unittest.TestCase):
    def test_put_get(self):
        backend = DuckDBBackend()
        self.assertTrue(backend.connect())
        backend.put("table1", {"data": [1, 2, 3]})
        self.assertEqual(backend.get("table1"), {"data": [1, 2, 3]})

class TestClusterRegistry(unittest.TestCase):
    def test_register(self):
        reg = ClusterRegistry()
        reg.register("redis", RedisBackend)
        self.assertIn("redis", reg.names())
        backend = reg.create("redis")
        self.assertIsNotNone(backend)

if __name__ == "__main__":
    unittest.main(verbosity=2)
