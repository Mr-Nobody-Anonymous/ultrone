#!/usr/bin/env python3
"""Tests for the Hardware package."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
import unittest
from hardware.backend import BackendRegistry, CPUBackend

class TestHardwareBackend(unittest.TestCase):
    def test_cpu_backend(self):
        cpu = CPUBackend()
        self.assertTrue(cpu.is_available())
        self.assertEqual(cpu.device_count(), 1)
        info = cpu.get_device_info()
        self.assertEqual(info["type"], "cpu")

class TestBackendRegistry(unittest.TestCase):
    def test_registry(self):
        reg = BackendRegistry()
        self.assertGreater(reg.count(), 0)
        cpu = reg.get("cpu")
        self.assertIsNotNone(cpu)
        self.assertIn("cpu", reg.available())

if __name__ == "__main__":
    unittest.main(verbosity=2)
