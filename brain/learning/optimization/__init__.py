"""Optimization engines module.

Provides interchangeable optimization algorithms:

- ``BaseOptimizer``: Abstract interface for all optimizers
- ``GeneticAlgorithm``: Population-based evolutionary optimization
- ``CMAES``: Covariance Matrix Adaptation Evolution Strategy
- ``DifferentialEvolution``: Differential evolution optimizer
- ``ParticleSwarm``: Particle Swarm Optimization
- ``SimulatedAnnealing``: Simulated annealing for global optimization
- ``BayesianOptimization``: Bayesian optimization with Gaussian Processes
- ``AntColony``: Ant Colony Optimization for discrete problems
- ``NSGA2``: Multi-objective evolutionary optimization (NSGA-II) 🆕
- ``CrossEntropyMethod``: Cross-Entropy Method for stochastic optimization 🆕
- ``MAPElites``: Quality Diversity optimization 🆕
"""

from .base import BaseOptimizer, OptimizerConfig, OptimizationResult
from .genetic_algorithm import GeneticAlgorithm, GAConfig
from .cma_es import CMAES, CMAESConfig
from .differential_evolution import DifferentialEvolution, DEConfig
from .particle_swarm import ParticleSwarm, PSOConfig
from .simulated_annealing import SimulatedAnnealing, SAConfig
from .bayesian_optimization import BayesianOptimization, BayesOptConfig
from .ant_colony import AntColony, AntColonyConfig
from .nsga2 import NSGA2, NSGA2Config
from .cross_entropy import CrossEntropyMethod, CEMConfig
from .map_elites import MAPElites, MAPElitesConfig

__all__ = [
    "BaseOptimizer", "OptimizerConfig", "OptimizationResult",
    "GeneticAlgorithm", "GAConfig",
    "CMAES", "CMAESConfig",
    "DifferentialEvolution", "DEConfig",
    "ParticleSwarm", "PSOConfig",
    "SimulatedAnnealing", "SAConfig",
    "BayesianOptimization", "BayesOptConfig",
    "AntColony", "AntColonyConfig",
    "NSGA2", "NSGA2Config",
    "CrossEntropyMethod", "CEMConfig",
    "MAPElites", "MAPElitesConfig",
]
