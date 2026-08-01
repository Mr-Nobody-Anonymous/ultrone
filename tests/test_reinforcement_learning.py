#!/usr/bin/env python3
"""Tests for Reinforcement Learning algorithms (Phase 2)."""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import unittest
import numpy as np
from brain.learning.rl.base import BaseRLAlgorithm, RLConfig, RLTrainer
from brain.learning.rl.ppo import PPO, PPOConfig
from brain.learning.rl.sac import SAC, SACConfig
from brain.learning.rl.dqn import DQN, DQNConfig
from brain.learning.rl.rainbow import RainbowDQN, RainbowConfig
from brain.learning.rl.self_play import SelfPlay, SelfPlayConfig
from brain.learning.rl.curriculum import CurriculumLearning, CurriculumConfig


class TestRLInterface(unittest.TestCase):
    def test_base_instantiation_fails(self):
        with self.assertRaises(TypeError):
            BaseRLAlgorithm(RLConfig())

    def test_ppo_implements_interface(self):
        p = PPO(PPOConfig())
        self.assertIsInstance(p, BaseRLAlgorithm)

    def test_sac_implements_interface(self):
        s = SAC(SACConfig())
        self.assertIsInstance(s, BaseRLAlgorithm)

    def test_dqn_implements_interface(self):
        d = DQN(DQNConfig())
        self.assertIsInstance(d, BaseRLAlgorithm)


class TestPPO(unittest.TestCase):
    def setUp(self):
        self.agent = PPO(PPOConfig())

    def test_select_action(self):
        obs = np.random.randn(8)
        action = self.agent.select_action(obs)
        self.assertIsNotNone(action)

    def test_get_stats(self):
        stats = self.agent.get_stats()
        self.assertIn("type", stats)


class TestSAC(unittest.TestCase):
    def setUp(self):
        self.agent = SAC(SACConfig())

    def test_select_action(self):
        obs = np.random.randn(8)
        action = self.agent.select_action(obs)
        self.assertIsNotNone(action)


class TestDQN(unittest.TestCase):
    def setUp(self):
        self.agent = DQN(DQNConfig())

    def test_select_action(self):
        obs = np.random.randn(8)
        action = self.agent.select_action(obs)
        self.assertIsNotNone(action)


class TestSelfPlay(unittest.TestCase):
    def setUp(self):
        inner = PPO(PPOConfig())
        self.agent = SelfPlay(inner)

    def test_get_stats(self):
        stats = self.agent.get_stats()
        self.assertIn("inner_algorithm", stats)


class TestCurriculum(unittest.TestCase):
    def setUp(self):
        self.curriculum = CurriculumLearning()

    def test_get_stats(self):
        stats = self.curriculum.get_stats()
        self.assertIn("num_tasks_completed", stats)


if __name__ == "__main__":
    unittest.main(verbosity=2)

