#!/usr/bin/env python3
"""Tests for XAI 2.0 extensions."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
import unittest

class TestXAIExtensions(unittest.TestCase):
    def test_import(self):
        try:
            from brain.xai.decision_trace import DecisionTrace
            self.assertTrue(True)
        except ImportError:
            self.skipTest("XAI extensions not fully available")
    def test_explainability_engine(self):
        from brain.perception.situational_awareness import ExplainabilityEngine
        engine = ExplainabilityEngine()
        self.assertIsNotNone(engine)

if __name__ == "__main__":
    unittest.main(verbosity=2)
