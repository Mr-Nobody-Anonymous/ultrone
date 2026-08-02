#!/usr/bin/env python3
"""Tests for AI Architecture Patterns (Phase 12)."""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import unittest
import numpy as np
from ai_architectures.base import AIArchitecture, AIArchitectureConfig
from ai_architectures.behavior_tree import BehaviorTree, BTConfig, Sequence, Selector, Action, Condition
from ai_architectures.goap import GOAP, GOAPConfig, GOAPAction, GOAPGoal
from ai_architectures.utility_ai import UtilityAI, UtilityAIConfig, Consideration, Option
from ai_architectures.bdi_agent import BDIAgent, BDIConfig, Belief, Desire, Intention
from ai_architectures.fsm import FSM, FSMConfig, State, Transition
from ai_architectures.hierarchical_fsm import HierarchicalFSM, HFSMConfig
from ai_architectures.blackboard_system import BlackboardSystem, BlackboardEntry
from ai_architectures.reactive_planning import ReactivePlanner, ReactivePlanConfig


class TestAIArchitectureInterface(unittest.TestCase):
    def test_base_instantiation_works(self):
        """Base class can be instantiated but decide() raises NotImplementedError."""
        base = AIArchitecture(AIArchitectureConfig())
        self.assertIsInstance(base, AIArchitecture)
        with self.assertRaises(NotImplementedError):
            base.decide({}, [], {})

    def test_behavior_tree_implements_interface(self):
        b = BehaviorTree()
        self.assertIsInstance(b, AIArchitecture)

    def test_goap_implements_interface(self):
        g = GOAP()
        self.assertIsInstance(g, AIArchitecture)

    def test_utility_ai_implements_interface(self):
        u = UtilityAI()
        self.assertIsInstance(u, AIArchitecture)

    def test_bdi_implements_interface(self):
        b = BDIAgent()
        self.assertIsInstance(b, AIArchitecture)

    def test_fsm_implements_interface(self):
        f = FSM()
        self.assertIsInstance(f, AIArchitecture)

    def test_hfsm_implements_interface(self):
        h = HierarchicalFSM()
        self.assertIsInstance(h, AIArchitecture)

    def test_blackboard_implements_interface(self):
        b = BlackboardSystem()
        self.assertIsInstance(b, AIArchitecture)

    def test_reactive_implements_interface(self):
        r = ReactivePlanner()
        self.assertIsInstance(r, AIArchitecture)


class TestBehaviorTree(unittest.TestCase):
    def setUp(self):
        self.bt = BehaviorTree()

    def test_decide(self):
        action = self.bt.decide({"state": "idle"})
        self.assertIsNotNone(action)

    def test_get_stats(self):
        stats = self.bt.get_stats()
        self.assertIn("type", stats)

    def test_reset(self):
        self.bt.decide({"state": "idle"})
        self.bt.reset()
        stats = self.bt.get_stats()
        self.assertIsNone(stats.get("last_action"))


class TestGOAP(unittest.TestCase):
    def setUp(self):
        self.goap = GOAP()

    def test_decide(self):
        action = self.goap.decide({"health": 50})
        self.assertIsNotNone(action)


class TestUtilityAI(unittest.TestCase):
    def setUp(self):
        self.uai = UtilityAI()

    def test_decide(self):
        action = self.uai.decide({"threat": 0.8})
        self.assertIsNotNone(action)


class TestBDI(unittest.TestCase):
    def setUp(self):
        self.bdi = BDIAgent()

    def test_decide(self):
        action = self.bdi.decide({"position": (0, 0)})
        self.assertIsNotNone(action)


class TestFSM(unittest.TestCase):
    def setUp(self):
        self.fsm = FSM()

    def test_decide(self):
        action = self.fsm.decide({"state": "patrol"})
        self.assertIsNotNone(action)

    def test_transition(self):
        self.fsm.add_transition("idle", "patrol", "start_patrol")
        self.fsm.decide({"state": "idle"})
        stats = self.fsm.get_stats()
        self.assertIn("current_state", stats)


class TestHierarchicalFSM(unittest.TestCase):
    def setUp(self):
        self.hfsm = HierarchicalFSM()

    def test_decide(self):
        action = self.hfsm.decide({"phase": "combat"})
        self.assertIsNotNone(action)


class TestBlackboardSystem(unittest.TestCase):
    def setUp(self):
        self.bb = BlackboardSystem()

    def test_share_and_read(self):
        self.bb.share("intel", "enemy spotted")
        result = self.bb.read("intel")
        self.assertEqual(result, "enemy spotted")

    def test_decide(self):
        action = self.bb.decide({"query": "intel"})
        self.assertIsNotNone(action)


class TestReactivePlanner(unittest.TestCase):
    def setUp(self):
        self.rp = ReactivePlanner()

    def test_decide(self):
        action = self.rp.decide({"event": "contact"})
        self.assertIsNotNone(action)


if __name__ == "__main__":
    unittest.main(verbosity=2)

