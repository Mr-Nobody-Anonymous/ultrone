#!/usr/bin/env python3
"""Tests for the Coding Agent package."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
import unittest
from coding_agent.agent import CodingAgent, TaskResult

class TestCodingAgent(unittest.TestCase):
    def test_analyze_code(self):
        agent = CodingAgent()
        result = agent.analyze_code("test.py")
        self.assertTrue(result.success)
        self.assertEqual(len(agent.history), 1)
    def test_write_code(self):
        agent = CodingAgent()
        result = agent.write_code("output.py", "print('hello')")
        self.assertTrue(result.success)
        self.assertIn("output.py", result.files_modified)
    def test_run_tests(self):
        agent = CodingAgent()
        result = agent.run_tests()
        self.assertTrue(result.success)

if __name__ == "__main__":
    unittest.main(verbosity=2)
