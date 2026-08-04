#!/usr/bin/env python3
"""Tests for the Security package."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
import unittest
from security.sandbox import Sandbox
from security.permissions import PermissionManager
from security.secret_manager import SecretManager

class TestSandbox(unittest.TestCase):
    def test_execute(self):
        sandbox = Sandbox()
        result = sandbox.execute("__result__ = 42")
        self.assertEqual(result, 42)
    def test_violation(self):
        sandbox = Sandbox()
        sandbox.execute("raise ValueError('test')")
        self.assertGreater(len(sandbox.violations), 0)

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
