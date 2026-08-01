"""
Quality Diversity (QD) Algorithms
==================================
A family of algorithms that search for a diverse set of high-performing
solutions, illuminating the relationship between behavior and performance.

Key QD algorithms:
1. MAP-Elites: Grid-based archive (already in map_elites_integration)
2. Novelty Search with Local Competition (NSLC)
3. CVT-MAP-Elites: Centroidal Voronoi Tesselation MAP-Elites
4. PGA-MAP-Elites: Policy Gradient assisted MAP-Elites
5. CMA-ME: Covariance Matrix Adaptation MAP-Elites

This module provides a unified interface for QD algorithms with
emphasis on the tactical/behavioral space.
"""

from __future__ import annotations

import logging
import math
import random
import numpy as np
from typing import Dict, List, Optional, Tuple, Callable, Any, Set
from dataclasses import dataclass, field
from abc import ABC, abstractmethod

logger = logging.getLogger("Ultrone.Brain.Learning.Evolutionary.QualityDiversity")


@dataclass
class QDArchiveEntry:
    """An entry in the quality diversity archive."""
    solution: np.ndarray
    fitness: float
    behavior: np.ndarray
    cell_index: Tuple[int, ...]
    age: int = 0

    def clone(self) -> QDArchiveEntry:
        return QDArchiveEntry(
            solution=self.solution.copy(),
            fitness=self.fitness,
            behavior=self.behavior.copy(),
            cell_index=self.cell_index,
            age=self.age,
        )


@dataclass
class QDArchive:
    """
    Archive that maps behavior space to high-performing solutions.
    
    Supports multiple behavior characterizations and distance metrics.
    """
    entries: Dict[Tuple[int, ...], QDArchiveEntry] = field(default_factory=dict)
    max_size: int = 10000
    n_bins: int = 10
    n_behavior_dims: int = 2

    def discretize(self, behavior: np.ndarray) -> Tuple[int, ...]:
        """Discretize continuous behavior into grid cell."""
        # Normalize and quantize
        normalized = np.clip(behavior, 0.0, 1.0)
        cell = tuple(int(b * self.n_bins) for b in normalized[:self.n_behavior_dims])
        return cell

    def add(self, solution: np.ndarray, fitness: float, behavior: np.ndarray) -> bool:
        """Add to archive if it improves the cell. Returns True if added."""
        cell = self.discretize(behavior)

        if cell not in self.entries or fitness > self.entries[cell].fitness:
            self.entries[cell] = QDArchiveEntry(
                solution=solution.copy(),
                fitness=fitness,
                behavior=behavior.copy(),
                cell_index=cell,
            )

            # Enforce size limit
            if len(self.entries) > self.max_size:
                self._prune()

            return True
        return False

    def _prune(self) -> None:
        """Remove worst-performing entries when over capacity."""
        if len(self.entries) <= self.max_size:
            return
        sorted_cells = sorted(self.entries.items(), key=lambda x: x[1].fitness)
        while len(self.entries) > self.max_size * 0.9:
            cell, _ = sorted_cells.pop(0)
            del self.entries[cell]

    def get_random(self) -> Optional[QDArchiveEntry]:
        """Get a random entry from the archive."""
        if not self.entries:
            return None
        cell = random.choice(list(self.entries.keys()))
        return self.entries[cell]

    def get_best(self) -> Optional[QDArchiveEntry]:
        """Get the highest-fitness entry."""
        if not self.entries:
            return None
        return max(self.entries.values(), key=lambda e: e.fitness)

    def coverage(self) -> float:
        """Fraction of cells filled."""
        total_cells = self.n_bins ** self.n_behavior_dims
        return len(self.entries) / max(1, total_cells)

    def size(self) -> int:
        return len(self.entries)


@dataclass
class QDConfig:
    """Configuration for Quality Diversity algorithms."""
    population_size: int = 100
    n_bins: int = 10
    n_behavior_dims: int = 2
    mutation_rate: float = 0.2
    mutation_strength: float = 0.1
    crossover_rate: float = 0.7
    archive_max_size: int = 10000
    n_children: int = 50  # Offspring per generation
    n_random_init: int = 50  # Random initialization batch
    exploration_weight: float = 0.5  # Weight for exploration vs exploitation


class QualityDiversity:
    """
    Quality Diversity algorithm framework.
    
    Searches for a diverse set of high-performing solutions
    by maintaining an archive of behaviors and rewarding
    both fitness and behavioral novelty.
    """

    def __init__(self, config: Optional[QDConfig] = None):
        self.config = config or QDConfig()
        self.archive = QDArchive(
            max_size=self.config.archive_max_size,
            n_bins=self.config.n_bins,
            n_behavior_dims=self.config.n_behavior_dims,
        )
        self.population: List[np.ndarray] = []
        self.generation = 0
        self._best_fitness: float = 0.0
        self._best_solution: Optional[np.ndarray] = None
        self._fitness_history: List[float] = []

    def initialize_population(self, genome_size: int) -> None:
        """Initialize population with random solutions."""
        self.population = []
        for _ in range(self.config.population_size):
            genome = np.random.randn(genome_size) * 0.5
            self.population.append(genome)

    def evaluate_and_add_to_archive(
        self,
        solution: np.ndarray,
        fitness_fn: Callable[[np.ndarray], float],
        behavior_fn: Callable[[np.ndarray], np.ndarray],
    ) -> float:
        """Evaluate a solution and add to archive. Returns fitness."""
        fitness = fitness_fn(solution)
        behavior = behavior_fn(solution)

        added = self.archive.add(solution, fitness, behavior)

        if fitness > self._best_fitness:
            self._best_fitness = fitness
            self._best_solution = solution.copy()

        return fitness

    def evaluate_population(
        self,
        fitness_fn: Callable[[np.ndarray], float],
        behavior_fn: Callable[[np.ndarray], np.ndarray],
    ) -> List[float]:
        """Evaluate all population members."""
        fitnesses = []
        for genome in self.population:
            fitness = self.evaluate_and_add_to_archive(genome, fitness_fn, behavior_fn)
            fitnesses.append(fitness)
        return fitnesses

    def select_parents(self) -> List[np.ndarray]:
        """Select parents using tournament selection."""
        parents = []
        for _ in range(self.config.population_size):
            t_size = 3
            tournament = random.sample(self.population, min(t_size, len(self.population)))

            # Score based on fitness + novelty bonus
            best_score = -float('inf')
            best = tournament[0]
            for genome in tournament:
                cell = self.archive.discretize(
                    np.zeros(self.config.n_behavior_dims)  # placeholder
                )
                # Novelty bonus: reward solutions in sparse cells
                novelty_bonus = 0.0
                if cell not in self.archive.entries:
                    novelty_bonus = self.config.exploration_weight

                score = self.config.exploration_weight * novelty_bonus
                best_score = score
                best = genome

            parents.append(best.copy())
        return parents

    def crossover(self, p1: np.ndarray, p2: np.ndarray) -> np.ndarray:
        """Uniform crossover."""
        child = p1.copy()
        for i in range(len(child)):
            if random.random() < 0.5:
                child[i] = p2[i]
        return child

    def mutate(self, genome: np.ndarray) -> np.ndarray:
        """Gaussian mutation."""
        child = genome.copy()
        for i in range(len(child)):
            if random.random() < self.config.mutation_rate:
                child[i] += random.gauss(0, self.config.mutation_strength)
        return child

    def evolve_generation(
        self,
        fitness_fn: Callable[[np.ndarray], float],
        behavior_fn: Callable[[np.ndarray], np.ndarray],
    ) -> None:
        """Run one generation of QD evolution."""
        # Evaluate population
        fitnesses = self.evaluate_population(fitness_fn, behavior_fn)
        avg_fitness = sum(fitnesses) / len(fitnesses) if fitnesses else 0.0
        self._fitness_history.append(avg_fitness)

        # Generate offspring
        offspring = []
        for _ in range(self.config.n_children):
            if random.random() < self.config.crossover_rate and len(self.population) >= 2:
                p1, p2 = random.sample(self.population, 2)
                child = self.crossover(p1, p2)
            else:
                parent = random.choice(self.population)
                child = parent.copy()

            child = self.mutate(child)
            offspring.append(child)

        # Evaluate offspring
        for child in offspring:
            self.evaluate_and_add_to_archive(child, fitness_fn, behavior_fn)

        # Select next population (mix of archive and random)
        next_population = []
        archive_entries = list(self.archive.entries.values())

        # Add archive solutions
        for entry in random.sample(archive_entries, min(len(archive_entries), self.config.population_size // 2)):
            next_population.append(entry.solution.copy())

        # Add random init for exploration
        for _ in range(self.config.n_random_init):
            genome = np.random.randn(len(self.population[0]) if self.population else 10) * 0.5
            next_population.append(genome)

        # Fill remaining with mutated archive solutions
        while len(next_population) < self.config.population_size:
            if archive_entries:
                entry = random.choice(archive_entries)
                child = self.mutate(entry.solution.copy())
            else:
                child = np.random.randn(len(self.population[0]) if self.population else 10) * 0.5
            next_population.append(child)

        self.population = next_population[:self.config.population_size]
        self.generation += 1

        logger.info(
            f"QD Gen {self.generation}: "
            f"Archive={self.archive.size()}/{self.archive.max_size} "
            f"Coverage={self.archive.coverage():.1%} "
            f"Best={self._best_fitness:.4f}"
        )

    def train(
        self,
        fitness_fn: Callable[[np.ndarray], float],
        behavior_fn: Callable[[np.ndarray], np.ndarray],
        n_generations: int = 100,
        genome_size: int = 10,
    ) -> QDArchive:
        """Train for multiple generations."""
        if not self.population:
            self.initialize_population(genome_size)

        for _ in range(n_generations):
            self.evolve_generation(fitness_fn, behavior_fn)

        return self.archive

    def get_stats(self) -> Dict[str, Any]:
        return {
            "generation": self.generation,
            "population_size": len(self.population),
            "archive_size": self.archive.size(),
            "archive_coverage": self.archive.coverage(),
            "best_fitness": self._best_fitness,
            "avg_fitness": (sum(self._fitness_history) / len(self._fitness_history))
                if self._fitness_history else 0.0,
        }

