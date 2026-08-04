#!/usr/bin/env python3
"""Tests for the UltroneOS package."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
import unittest
from ultrone_os.kernel import Kernel
from ultrone_os.scheduler import OSScheduler
from ultrone_os.service_registry import ServiceRegistry

class TestKernel(unittest.TestCase):
    def test_start_stop(self):
        kernel = Kernel()
        kernel.start()
        self.assertTrue(kernel.is_running)
        kernel.stop()
        self.assertFalse(kernel.is_running)
    def test_register_service(self):
        kernel = Kernel()
        kernel.register_service("test", {"data": 42})
        self.assertEqual(kernel.service_names, ["test"])
        self.assertEqual(kernel.get_service("test")["data"], 42)

class TestOSScheduler(unittest.TestCase):
    def test_spawn_kill(self):
        scheduler = OSScheduler()
        pid = scheduler.spawn("test_process", priority=5)
        self.assertEqual(scheduler.process_count, 1)
        self.assertTrue(scheduler.kill(pid))
        self.assertEqual(scheduler.process_count, 0)
    def test_schedule(self):
        scheduler = OSScheduler()
        scheduler.spawn("low", priority=1)
        scheduler.spawn("high", priority=10)
        proc = scheduler.schedule()
        self.assertEqual(proc.name, "high")

class TestServiceRegistry(unittest.TestCase):
    def test_register_lookup(self):
        reg = ServiceRegistry()
        reg.register("api", "http://localhost:8080")
        service = reg.lookup("api")
        self.assertEqual(service["endpoint"], "http://localhost:8080")
        self.assertIn("api", reg.healthy_services())
    def test_unregister(self):
        reg = ServiceRegistry()
        reg.register("api", "http://localhost:8080")
        self.assertTrue(reg.unregister("api"))
        self.assertEqual(reg.count, 0)

if __name__ == "__main__":
    unittest.main(verbosity=2)
