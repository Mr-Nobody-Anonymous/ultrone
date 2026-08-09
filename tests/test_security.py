#!/usr/bin/env python3
"""Tests for the Security package."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
import unittest
from security.sandbox import Sandbox, SandboxResult
from security.permissions import PermissionManager
from security.secret_manager import SecretManager

class TestSandbox(unittest.TestCase):
    def test_execute(self):
        sandbox = Sandbox()
        result = sandbox.execute("__result__ = 42")
        self.assertIsInstance(result, SandboxResult)
        self.assertTrue(result.success)
        self.assertEqual(result.output, 42)

    def test_violation(self):
        sandbox = Sandbox()
        result = sandbox.execute("raise ValueError('test')")
        self.assertFalse(result.success)
        self.assertGreater(len(sandbox.violations), 0)

    def test_timeout(self):
        sandbox = Sandbox(timeout=1.0)
        result = sandbox.execute("import time; time.sleep(10)")
        self.assertTrue(result.timed_out or not result.success)

    def test_stats(self):
        sandbox = Sandbox()
        sandbox.execute("__result__ = 1")
        stats = sandbox.get_stats()
        self.assertEqual(stats["type"], "SecureSandbox")
        self.assertGreaterEqual(stats["total_executions"], 1)

class TestPermissions(unittest.TestCase):
    def test_grant_check(self):
        pm = PermissionManager()
        pm.grant("admin", "delete")
        self.assertTrue(pm.check("admin", "delete"))
        self.assertFalse(pm.check("admin", "create"))

class TestSecretManager(unittest.TestCase):
    def test_store_retrieve(self):
        sm = SecretManager(master_key="test")
        sm.store("api_key", "secret123")
        self.assertEqual(sm.retrieve("api_key"), "secret123")
        self.assertTrue(sm.delete("api_key"))
        self.assertIsNone(sm.retrieve("api_key"))

if __name__ == "__main__":
    unittest.main(verbosity=2)
