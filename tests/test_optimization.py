#!/usr/bin/env python3
"""Tests for Optimization engines (Phase 4)."""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import unittest
import numpy as np
from brain.learning.optimization.base import BaseOptimizer, OptimizerConfig
from brain.learning.optimization.genetic_algorithm import GeneticAlgorithm, GAConfig
from brain.learning.optimization.particle_swarm import ParticleSwarm, PSOConfig
from brain.learning.optimization.simulated_annealing import SimulatedAnnealing, SAConfig
from brain.learning.optimization.bayesian_optimization import BayesianOptimization, BayesOptConfig


def sphere(x):
    return float(np.sum(x ** 2))


class TestOptimizerInterface(unittest.TestCase):
    def test_base_instantiation_fails(self):
        with self.assertRaises(TypeError):
            BaseOptimizer(OptimizerConfig())

    def test_ga_implements_interface(self):
        g = GeneticAlgorithm()
        self.assertIsInstance(g, BaseOptimizer)

    def test_pso_implements_interface(self):
        p = ParticleSwarm()
        self.assertIsInstance(p, BaseOptimizer)

    def test_sa_implements_interface(self):
        s = SimulatedAnnealing()
        self.assertIsInstance(s, BaseOptimizer)


class TestGeneticAlgorithm(unittest.TestCase):
    def setUp(self):
        self.opt = GeneticAlgorithm(GAConfig(population_size=20, max_iterations=30))

    def test_optimize_sphere(self):
        best_val, best_x = self.opt.optimize(sphere, np.array([[-5, 5], [-5, 5]]), max_iter=20)
        self.assertLess(best_val, 5.0)

    def test_get_stats(self):
        self.opt.optimize(sphere, np.array([[-5, 5], [-5, 5]]), max_iter=5)
        stats = self.opt.get_stats()
        self.assertIn("type", stats)


class TestParticleSwarm(unittest.TestCase):
    def setUp(self):
        self.opt = ParticleSwarm(PSOConfig(population_size=10, max_iterations=30))

    def test_optimize_sphere(self):
        best_val, best_x = self.opt.optimize(sphere, np.array([[-5, 5], [-5, 5]]), max_iter=20)
        self.assertLess(best_val, 5.0)


class TestSimulatedAnnealing(unittest.TestCase):
    def setUp(self):
        self.opt = SimulatedAnnealing(SAConfig(max_iterations=100))

    def test_optimize_sphere(self):
        best_val, best_x = self.opt.optimize(sphere, np.array([[-5, 5]]), max_iter=50)
        self.assertIsNotNone(best_val)


class TestBayesianOptimization(unittest.TestCase):
    def setUp(self):
        self.opt = BayesianOptimization(BayesOptConfig(n_initial_points=5, n_iterations=20))

    def test_optimize_sphere(self):
        best_val, best_x = self.opt.optimize(sphere, np.array([[-5, 5], [-5, 5]]), max_iter=15)
        self.assertIsNotNone(best_val)


if __name__ == "__main__":
    unittest.main(verbosity=2)

