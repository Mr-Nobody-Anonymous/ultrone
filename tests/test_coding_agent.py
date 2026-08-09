#!/usr/bin/env python3
"""Tests for the Coding Agent package.

The CodingAgent has been upgraded to a real software-engineering agent, so
these tests create an actual source file before analyzing rather than relying
on the previous stub behavior.
"""
import os
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import unittest

from coding_agent.agent import CodingAgent, TaskResult


class TestCodingAgent(unittest.TestCase):
    def _make_workspace(self):
        """Create a temp workspace with a sample source file."""
        tmp = tempfile.mkdtemp()
        with open(os.path.join(tmp, "test.py"), "w", encoding="utf-8") as fh:
            fh.write("def add(a, b):\n    return a + b\n")
        return tmp

    def test_analyze_code(self):
        workspace = self._make_workspace()
        agent = CodingAgent(workspace=workspace)
        result = agent.analyze_code("test.py")
        self.assertTrue(result.success)
        self.assertEqual(len(agent.history), 1)

    def test_write_code(self):
        agent = CodingAgent(workspace=".")
        result = agent.write_code("output.py", "print('hello')")
        self.assertTrue(result.success)
        self.assertIn("output.py", result.files_modified)
        # Cleanup the file created by the test.
        out_path = os.path.join(".", "output.py")
        if os.path.exists(out_path):
            os.remove(out_path)

    def test_run_tests(self):
        workspace = self._make_workspace()
        # Add a real test file so pytest has something to collect.
        test_dir = os.path.join(workspace, "tests")
        os.makedirs(test_dir, exist_ok=True)
        with open(os.path.join(test_dir, "test_sample.py"), "w", encoding="utf-8") as fh:
            fh.write(
                "def test_add():\n"
                "    assert 1 + 1 == 2\n"
            )
        agent = CodingAgent(workspace=workspace)
        result = agent.run_tests("tests/test_sample.py")
        self.assertTrue(result.success)


if __name__ == "__main__":
    unittest.main(verbosity=2)
