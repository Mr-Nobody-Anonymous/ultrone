#!/usr/bin/env python3
"""Tests for Game Theory modules (Phase 6)."""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import unittest
import numpy as np
from brain.reasoning.game_theory.nash_equilibrium import NashEquilibrium, NashConfig
from brain.reasoning.game_theory.stackelberg import StackelbergGame, StackelbergConfig
from brain.reasoning.game_theory.minimax import MinimaxSearch, MinimaxConfig
from brain.reasoning.game_theory.cfr import CFR, CFRConfig
from brain.reasoning.game_theory.auction import AuctionMechanism, AuctionConfig
from brain.reasoning.game_theory.zero_sum import ZeroSumGame, ZeroSumConfig
from brain.reasoning.game_theory.cooperative import CooperativeGame, CooperativeConfig


class TestNashEquilibrium(unittest.TestCase):
    def setUp(self):
        self.solver = NashEquilibrium()

    def test_solve_2x2(self):
        payoff_matrix = np.array([[[3, 0], [5, 1]], [[3, 5], [0, 1]]])
        result = self.solver.solve(payoff_matrix)
        self.assertIsNotNone(result)

    def test_get_stats(self):
        stats = self.solver.get_stats()
        self.assertIn("num_players", stats)


class TestStackelberg(unittest.TestCase):
    def setUp(self):
        self.game = StackelbergGame()

    def test_solve(self):
        result = self.game.solve(num_actions=5)
        self.assertIsNotNone(result)


class TestMinimax(unittest.TestCase):
    def setUp(self):
        self.search = MinimaxSearch()

    def test_search(self):
        result = self.search.search(depth=3)
        self.assertIsNotNone(result)

    def test_get_stats(self):
        stats = self.search.get_stats()
        self.assertIn("nodes_evaluated", stats)


class TestCFR(unittest.TestCase):
    def setUp(self):
        self.cfr = CFR()

    def test_train(self):
        result = self.cfr.train(iterations=10)
        self.assertIsNotNone(result)


class TestAuction(unittest.TestCase):
    def setUp(self):
        self.auction = AuctionMechanism()

    def test_run_auction(self):
        bids = {"A": 100, "B": 80, "C": 120}
        result = self.auction.run_auction(bids)
        self.assertIsNotNone(result)


class TestZeroSum(unittest.TestCase):
    def setUp(self):
        self.game = ZeroSumGame()

    def test_solve(self):
        result = self.game.solve(payoff_matrix=np.array([[1, -1], [-1, 1]]))
        self.assertIsNotNone(result)


class TestCooperative(unittest.TestCase):
    def setUp(self):
        self.game = CooperativeGame()

    def test_compute_shapley(self):
        values = {"A": 10, "B": 15, "C": 25}
        result = self.game.compute_shapley(values)
        self.assertIsNotNone(result)


if __name__ == "__main__":
    unittest.main(verbosity=2)

