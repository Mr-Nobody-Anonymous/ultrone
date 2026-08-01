#!/usr/bin/env python3
"""Tests for Explainable AI modules (Phase 9)."""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import unittest
import numpy as np
from brain.xai.decision_trace import DecisionTrace, DecisionTraceConfig
from brain.xai.shap_explainer import SHAPExplainer
from brain.xai.lime_explainer import LIMEExplainer
from brain.xai.counterfactual import CounterfactualExplainer, CounterfactualConfig
from brain.xai.confidence_calibration import ConfidenceCalibration
from brain.xai.reasoning_graph import ReasoningGraph


class TestDecisionTrace(unittest.TestCase):
    def setUp(self):
        self.dt = DecisionTrace()

    def test_trace(self):
        trace = self.dt.trace({"input": 1.0}, "action_1")
        self.assertIsNotNone(trace)

    def test_get_stats(self):
        stats = self.dt.get_stats()
        self.assertIn("num_traces", stats)


class TestSHAPExplainer(unittest.TestCase):
    def setUp(self):
        self.explainer = SHAPExplainer()

    def test_explain(self):
        result = self.explainer.explain(np.random.randn(10, 5))
        self.assertIsNotNone(result)

    def test_get_stats(self):
        stats = self.explainer.get_stats()
        self.assertIn("type", stats)


class TestLIMEExplainer(unittest.TestCase):
    def setUp(self):
        self.explainer = LIMEExplainer()

    def test_explain(self):
        result = self.explainer.explain(np.random.randn(10, 5))
        self.assertIsNotNone(result)


class TestCounterfactualExplainer(unittest.TestCase):
    def setUp(self):
        self.explainer = CounterfactualExplainer()

    def test_explain(self):
        result = self.explainer.explain(np.random.randn(10, 5))
        self.assertIsNotNone(result)


class TestConfidenceCalibration(unittest.TestCase):
    def setUp(self):
        self.cal = ConfidenceCalibration()

    def test_calibrate(self):
        result = self.cal.calibrate(np.random.rand(100), np.random.randint(0, 2, 100))
        self.assertIsNotNone(result)


class TestReasoningGraph(unittest.TestCase):
    def setUp(self):
        self.rg = ReasoningGraph()

    def test_build(self):
        graph = self.rg.build({"action": "strike", "reason": "threat_detected"})
        self.assertIsNotNone(graph)

    def test_get_stats(self):
        stats = self.rg.get_stats()
        self.assertIn("num_nodes", stats)


if __name__ == "__main__":
    unittest.main(verbosity=2)

