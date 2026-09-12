"""
Novelty Search
==============
Rewards behavioral novelty over pure fitness to avoid deception
and discover diverse solutions.

Paper: "Abandoning Objectives: Evolution Through the Search for Novelty Alone"
(Lehman & Stanley, 2011)

Key idea: Instead of optimizing for a goal, reward individuals for
behavior that is different from what has been seen before.
"""

from __future__ import annotations

import math
import random
import numpy as np
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Callable, Any, Set
from collections import deque


@dataclass
class BehaviorDescriptor:
    """A compressed representation of an agent's behavior."""
    features: np.ndarray  # The behavior characterization vector

    def distance_to(self, other: BehaviorDescriptor) -> float:
        """Euclidean distance between behavior descriptors."""
        return float(np.linalg.norm(self.features - other.features))


@dataclass
class NoveltyArchive:
    """Archive of past behaviors for novelty computation."""
    entries: List[BehaviorDescriptor] = field(default_factory=list)
    max_size: int = 1000

    def add(self, behavior: BehaviorDescriptor) -> None:
        """Add a behavior to the archive (sporadic sampling)."""
        if random.random() < 0.02 or len(self.entries) < self.max_size:
            self.entries.append(behavior)
            if len(self.entries) > self.max_size:
                self.entries.pop(0)

    def novelty_score(self, behavior: BehaviorDescriptor, k: int = 15) -> float:
        """
        Compute novelty as average distance to k nearest neighbors.
        
        Scores are computed against both the current population and archive.
        """
        if not self.entries:
            return 1.0  # First individual is always novel

        # Sample distances to archive entries
        distances = [behavior.distance_to(entry) for entry in self.entries]
        distances.sort()
        k_nearest = distances[:min(k, len(distances))]

        if not k_nearest:
            return 0.0

        return sum(k_nearest) / len(k_nearest)


@dataclass
class NoveltySearchConfig:
    """Configuration for Novelty Search."""
    population_size: int = 100
    mutation_rate: float = 0.2
    mutation_strength: float = 0.1
    crossover_prob: float = 0.7
    k_nearest: int = 15  # K for nearest neighbors
    archive_max_size: int = 1000
    elitism: int = 2
    novelty_weight: float = 1.0  # Weight of novelty vs fitness
    fitness_weight: float = 0.0  # Only used when novelty_weight < 1


class Individual:
    """An individual in the novelty search population."""

    def __init__(self, genome: np.ndarray):
        self.genome = genome.copy()
        self.fitness: float = 0.0
        self.novelty: float = 0.0
        self.behavior: Optional[BehaviorDescriptor] = None

    def clone(self) -> Individual:
        ind = Individual(self.genome)
        ind.fitness = self.fitness
        ind.novelty = self.novelty
        ind.behavior = self.behavior
        return ind


class NoveltySearch:
    """
    Novelty Search algorithm.

    Rewards individuals based on how different their behavior is
    from previously seen behaviors, rather than how close they are
    to a fixed objective.
    """

    def __init__(self, config: Optional[NoveltySearchConfig] = None):
        self.config = config or NoveltySearchConfig()
        self.population: List[Individual] = []
        self.archive = NoveltyArchive(max_size=self.config.archive_max_size)
        self.generation = 0
        self.best_individual: Optional[Individual] = None
        self.best_novelty: float = -float('inf')
        self._novelty_history: List[float] = []

    def initialize_population(self, genome_size: int) -> None:
        """Create initial random population."""
        self.population = []
        for _ in range(self.config.population_size):
            genome = np.random.randn(genome_size) * 0.5
            self.population.append(Individual(genome))

    def evaluate_population(
        self,
        behavior_fn: Callable[[np.ndarray], BehaviorDescriptor],
        fitness_fn: Optional[Callable[[np.ndarray], float]] = None,
    ) -> None:
        """Evaluate behaviors and compute novelty for all individuals."""
        # Compute behaviors
        for ind in self.population:
            ind.behavior = behavior_fn(ind.genome)
            if fitness_fn is not None:
                ind.fitness = fitness_fn(ind.genome)
            else:
                ind.fitness = 0.0

        # Compute novelty scores
        for ind in self.population:
            ind.novelty = self.archive.novelty_score(ind.behavior, self.config.k_nearest)
            self.archive.add(ind.behavior)

        # Compute combined scores
        for ind in self.population:
            combined = (self.config.novelty_weight * ind.novelty +
                        self.config.fitness_weight * ind.fitness)
            ind.fitness = combined

        # Track best
        max_novelty = max(ind.novelty for ind in self.population)
        if max_novelty > self.best_novelty:
            self.best_novelty = max_novelty
            best_idx = max(range(len(self.population)), key=lambda i: self.population[i].novelty)
            self.best_individual = self.population[best_idx].clone()

    def select_parents(self) -> List[Individual]:
        """Tournament selection based on novelty score."""
        parents = []
        pop_size = len(self.population)

        for _ in range(pop_size):
            t_size = 3
            tournament = random.sample(self.population, min(t_size, pop_size))
            winner = max(tournament, key=lambda ind: ind.fitness)
            parents.append(winner.clone())

        return parents

    def crossover(self, p1: Individual, p2: Individual) -> Individual:
        """Uniform crossover between two parents."""
        child_genome = p1.genome.copy()
        for i in range(len(child_genome)):
            if random.random() < 0.5:
                child_genome[i] = p2.genome[i]
        return Individual(child_genome)

    def mutate(self, ind: Individual) -> Individual:
        """Gaussian mutation."""
        child = ind.clone()
        for i in range(len(child.genome)):
            if random.random() < self.config.mutation_rate:
                child.genome[i] += random.gauss(0, self.config.mutation_strength)
        return child

    def evolve_generation(
        self,
        behavior_fn: Callable[[np.ndarray], BehaviorDescriptor],
        fitness_fn: Optional[Callable[[np.ndarray], float]] = None,
    ) -> None:
        """Run one generation of novelty search."""
        self.evaluate_population(behavior_fn, fitness_fn)

        # Sort by fitness
        self.population.sort(key=lambda ind: ind.fitness, reverse=True)

        # Elitism
        elites = [ind.clone() for ind in self.population[:self.config.elitism]]

        # Selection and reproduction
        parents = self.select_parents()
        next_population = list(elites)

        while len(next_population) < self.config.population_size:
            p1, p2 = random.sample(parents, 2)
            if random.random() < self.config.crossover_prob:
                child = self.crossover(p1, p2)
            else:
                child = p1.clone()
            child = self.mutate(child)
            next_population.append(child)

        self.population = next_population[:self.config.population_size]
        self.generation += 1
        avg_novelty = sum(ind.novelty for ind in self.population) / len(self.population)
        self._novelty_history.append(avg_novelty)

    def train(
        self,
        behavior_fn: Callable[[np.ndarray], BehaviorDescriptor],
        fitness_fn: Optional[Callable[[np.ndarray], float]] = None,
        n_generations: int = 100,
        genome_size: int = 10,
    ) -> Individual:
        """Train for multiple generations."""
        if not self.population:
            self.initialize_population(genome_size)

        for _ in range(n_generations):
            self.evolve_generation(behavior_fn, fitness_fn)

        return self.best_individual if self.best_individual else self.population[0]

    def get_stats(self) -> Dict[str, Any]:
        return {
            "generation": self.generation,
            "population_size": len(self.population),
            "archive_size": len(self.archive.entries),
            "best_novelty": self.best_novelty,
            "avg_novelty": (sum(self._novelty_history) / len(self._novelty_history))
                if self._novelty_history else 0.0,
}

