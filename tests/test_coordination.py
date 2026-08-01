#!/usr/bin/env python3
"""Tests for Multi-Agent Coordination (Phase 3)."""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import unittest
import numpy as np
from brain.reasoning.coordination.base import BaseCoordinator, CoordinationConfig
from brain.reasoning.coordination.consensus import ConsensusProtocol, ConsensusConfig
from brain.reasoning.coordination.task_allocation import TaskAllocation, TaskAllocationConfig
from brain.reasoning.coordination.contract_net import ContractNet, ContractNetConfig
from brain.reasoning.coordination.blackboard import BlackboardSystem, BlackboardConfig
from brain.reasoning.coordination.formation_control import FormationControl, FormationConfig
from brain.reasoning.coordination.swarm_coordination import SwarmCoordination, SwarmConfig
from brain.reasoning.coordination.team_reasoning import TeamReasoning, TeamReasoningConfig


class TestCoordinationInterface(unittest.TestCase):
    def test_base_instantiation_fails(self):
        with self.assertRaises(TypeError):
            BaseCoordinator(CoordinationConfig())

    def test_consensus_implements_interface(self):
        c = ConsensusProtocol()
        self.assertIsInstance(c, BaseCoordinator)

    def test_task_allocation_implements_interface(self):
        t = TaskAllocation()
        self.assertIsInstance(t, BaseCoordinator)

    def test_contract_net_implements_interface(self):
        c = ContractNet()
        self.assertIsInstance(c, BaseCoordinator)

    def test_blackboard_implements_interface(self):
        b = BlackboardSystem()
        self.assertIsInstance(b, BaseCoordinator)

    def test_formation_control_implements_interface(self):
        f = FormationControl()
        self.assertIsInstance(f, BaseCoordinator)

    def test_swarm_implements_interface(self):
        s = SwarmCoordination()
        self.assertIsInstance(s, BaseCoordinator)

    def test_team_reasoning_implements_interface(self):
        t = TeamReasoning()
        self.assertIsInstance(t, BaseCoordinator)


class TestConsensus(unittest.TestCase):
    def setUp(self):
        self.coord = ConsensusProtocol()

    def test_propose(self):
        result = self.coord.propose("test_value")
        self.assertIsNotNone(result)

    def test_get_stats(self):
        stats = self.coord.get_stats()
        self.assertIn("type", stats)


class TestTaskAllocation(unittest.TestCase):
    def setUp(self):
        self.coord = TaskAllocation()

    def test_allocate(self):
        result = self.coord.allocate({"task_1": 1.0})
        self.assertIsNotNone(result)


class TestFormationControl(unittest.TestCase):
    def setUp(self):
        self.coord = FormationControl()

    def test_get_stats(self):
        stats = self.coord.get_stats()
        self.assertIn("type", stats)


class TestSwarmCoordination(unittest.TestCase):
    def setUp(self):
        self.coord = SwarmCoordination()

    def test_get_stats(self):
        stats = self.coord.get_stats()
        self.assertIn("swarm_size", stats)


if __name__ == "__main__":
    unittest.main(verbosity=2)

