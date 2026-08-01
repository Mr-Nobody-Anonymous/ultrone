"""
NSGA-III: Many-Objective Evolutionary Optimization
===================================================
Extends NSGA-II to handle many-objective problems (3+ objectives).

Paper: "An Evolutionary Many-Objective Optimization Algorithm Using
Reference-Point-Based Non-dominated Sorting Approach, Part I:
Solving Problems With Box Constraints" (Deb & Jain, 2014)

Key innovations:
- Reference points on a hyperplane for diversity preservation
- Adaptive normalization of objective space
- Association operator to link solutions to reference points
- Niching preservation via niche count
"""

from __future__ import annotations

import logging
import math
import random
import numpy as np
from typing import Dict, List, Optional, Tuple, Callable, Any, Set
from dataclasses import dataclass, field
from itertools import combinations

logger = logging.getLogger("Ultrone.Brain.Learning.Evolutionary.NSGA3")


def generate_reference_points(n_objectives: int, n_partitions: int = 4) -> np.ndarray:
    """
    Generate reference points on a simplex using Das and Dennis's method.
    
    Creates uniformly distributed points on a hyperplane.
    """
    def recursive_combinations(n, p, current=None, depth=0):
        if current is None:
            current = []
        if depth == n - 1:
            current.append(p)
            yield np.array(current)
        else:
            for i in range(p + 1):
                yield from recursive_combinations(n, p - i, current + [i], depth + 1)

    ref_points = []
    for combo in recursive_combinations(n_objectives, n_partitions):
        ref_points.append(combo / n_partitions)

    return np.array(ref_points)


@dataclass
class NSGA3Config:
    """Configuration for NSGA-III."""
    population_size: int = 100
    n_objectives: int = 3
    n_partitions: int = 4  # Controls number of reference points
    crossover_prob: float = 0.9
    mutation_prob: float = 0.1
    mutation_strength: float = 0.1
    n_generations: int = 100
    n_elites: int = 2


class NSGA3Individual:
    """An individual in the NSGA-III population."""

    def __init__(self, genome: np.ndarray):
        self.genome = genome.copy()
        self.objectives: np.ndarray = np.zeros(0)  # Multi-objective values
        self.rank: int = 0
        self.crowding_distance: float = 0.0
        self.ref_point_index: int = -1
        self.distance_to_ref: float = float('inf')

    def clone(self) -> NSGA3Individual:
        ind = NSGA3Individual(self.genome)
        ind.objectives = self.objectives.copy()
        ind.rank = self.rank
        ind.crowding_distance = self.crowding_distance
        return ind


class NSGA3:
    """
    NSGA-III: Reference-point based many-objective evolutionary algorithm.

    Handles 3+ objectives by using reference points to maintain diversity
    instead of crowding distance (which works poorly in high dimensions).
    """

    def __init__(self, config: Optional[NSGA3Config] = None):
        self.config = config or NSGA3Config()
        self.population: List[NSGA3Individual] = []
        self.generation = 0
        self.reference_points = generate_reference_points(
            self.config.n_objectives, self.config.n_partitions,
        )
        self.best_individuals: List[NSGA3Individual] = []
        self._pareto_front_history: List[int] = []

    def initialize_population(self, genome_size: int, bounds: Optional[List[Tuple[float, float]]] = None) -> None:
        """Initialize population with random genomes."""
        self.population = []
        for _ in range(self.config.population_size):
            if bounds:
                genome = np.array([random.uniform(b[0], b[1]) for b in bounds])
            else:
                genome = np.random.randn(genome_size) * 0.5
            self.population.append(NSGA3Individual(genome))

    def evaluate_population(self, objective_fn: Callable[[np.ndarray], np.ndarray]) -> None:
        """Evaluate all individuals on all objectives."""
        for ind in self.population:
            ind.objectives = objective_fn(ind.genome)

    def dominates(self, obj1: np.ndarray, obj2: np.ndarray) -> bool:
        """Check if obj1 dominates obj2 (all objectives better or equal, at least one strictly)."""
        return np.all(obj1 <= obj2) and np.any(obj1 < obj2)

    def non_dominated_sort(self) -> List[int]:
        """Perform non-dominated sorting. Returns Pareto front ranks."""
        n = len(self.population)
        domination_count = np.zeros(n, dtype=int)
        dominated_set = [set() for _ in range(n)]
        fronts = []

        # Compute domination relationships
        for i in range(n):
            for j in range(i + 1, n):
                if self.dominates(self.population[i].objectives, self.population[j].objectives):
                    dominated_set[i].add(j)
                    domination_count[j] += 1
                elif self.dominates(self.population[j].objectives, self.population[i].objectives):
                    dominated_set[j].add(i)
                    domination_count[i] += 1

        # Find first front
        current_front = [i for i in range(n) if domination_count[i] == 0]
        fronts.append(current_front)

        # Subsequent fronts
        while current_front:
            next_front = []
            for i in current_front:
                for j in dominated_set[i]:
                    domination_count[j] -= 1
                    if domination_count[j] == 0:
                        next_front.append(j)
            current_front = next_front
            if current_front:
                fronts.append(current_front)

        # Assign ranks
        for rank, front in enumerate(fronts):
            for i in front:
                self.population[i].rank = rank

        return [self.population[i].rank for i in range(n)]

    def normalize_objectives(self, individuals: List[NSGA3Individual]) -> np.ndarray:
        """Normalize objectives to [0, 1] range."""
        if not individuals:
            return np.array([])

        obj_matrix = np.array([ind.objectives for ind in individuals])
        obj_min = np.min(obj_matrix, axis=0)
        obj_max = np.max(obj_matrix, axis=0)
        obj_range = np.maximum(obj_max - obj_min, 1e-10)

        return (obj_matrix - obj_min) / obj_range

    def associate_to_reference_points(self, individuals: List[NSGA3Individual]) -> None:
        """Associate each individual to the closest reference point."""
        if not individuals or len(self.reference_points) == 0:
            return

        normalized = self.normalize_objectives(individuals)

        for i, ind in enumerate(individuals):
            distances = np.linalg.norm(self.reference_points - normalized[i], axis=1)
            ind.ref_point_index = int(np.argmin(distances))
            ind.distance_to_ref = float(np.min(distances))

    def niching_select(self, front: List[NSGA3Individual], n_remaining: int) -> List[NSGA3Individual]:
        """Select individuals from a front using reference point niching."""
        self.associate_to_reference_points(front)

        # Count niche occupancy
        niche_count = {}
        for ind in front:
            rp = ind.ref_point_index
            niche_count[rp] = niche_count.get(rp, 0) + 1

        selected = []
        available = list(front)

        # Find reference point with smallest niche count
        while len(selected) < n_remaining and available:
            # Find RP with minimum niche count among available individuals
            min_niche = float('inf')
            best_rp = -1
            for ind in available:
                if niche_count.get(ind.ref_point_index, 0) < min_niche:
                    min_niche = niche_count.get(ind.ref_point_index, 0)
                    best_rp = ind.ref_point_index

            if best_rp == -1:
                break

            # Select individual closest to this RP
            candidates = [ind for ind in available if ind.ref_point_index == best_rp]
            if candidates:
                best = min(candidates, key=lambda x: x.distance_to_ref)
                selected.append(best)
                available.remove(best)
                niche_count[best_rp] = niche_count.get(best_rp, 0) + 1
            else:
                # No candidates for this RP, move to next
                niche_count[best_rp] = float('inf')

        # Fill remaining slots with any available individuals
        while len(selected) < n_remaining and available:
            selected.append(available.pop(0))

        return selected

    def select_parents(self) -> List[NSGA3Individual]:
        """Tournament selection based on rank and crowding distance."""
        parents = []
        for _ in range(self.config.population_size):
            t_size = 3
            tournament = random.sample(self.population, min(t_size, len(self.population)))
            # Select by rank, then by distance to ref point
            best = min(tournament, key=lambda x: (x.rank, x.distance_to_ref))
            parents.append(best)
        return parents

    def crossover(self, p1: NSGA3Individual, p2: NSGA3Individual) -> NSGA3Individual:
        """Simulated binary crossover (SBX)."""
        child_genome = p1.genome.copy()
        for i in range(len(child_genome)):
            if random.random() < self.config.crossover_prob * 0.5:
                # SBX operator
                u = random.random()
                beta = (2 * u) ** (1 / 2) if u <= 0.5 else (1 / (2 * (1 - u))) ** (1 / 2)
                child_genome[i] = 0.5 * ((1 + beta) * p1.genome[i] + (1 - beta) * p2.genome[i])
        return NSGA3Individual(child_genome)

    def mutate(self, ind: NSGA3Individual) -> NSGA3Individual:
        """Polynomial mutation."""
        child = ind.clone()
        for i in range(len(child.genome)):
            if random.random() < self.config.mutation_prob:
                child.genome[i] += random.gauss(0, self.config.mutation_strength)
        return child

    def evolve_generation(self, objective_fn: Callable[[np.ndarray], np.ndarray]) -> None:
        """Run one generation of NSGA-III."""
        # Evaluate
        self.evaluate_population(objective_fn)

        # Non-dominated sorting
        self.non_dominated_sort()

        # Sort by rank
        sorted_pop = sorted(self.population, key=lambda x: x.rank)

        # Select next generation using reference point niching
        next_pop = []
        rank = 0
        while len(next_pop) < self.config.population_size and rank < len(sorted_pop):
            front = [ind for ind in sorted_pop if ind.rank == rank]
            if len(next_pop) + len(front) <= self.config.population_size:
                next_pop.extend(front)
            else:
                n_remaining = self.config.population_size - len(next_pop)
                selected = self.niching_select(front, n_remaining)
                next_pop.extend(selected)
            rank += 1

        self.population = next_pop

        # Track Pareto front size
        pareto_size = sum(1 for ind in self.population if ind.rank == 0)
        self._pareto_front_history.append(pareto_size)

        # Selection and reproduction
        parents = self.select_parents()
        offspring = []
        while len(offspring) < self.config.population_size:
            p1, p2 = random.sample(parents, 2)
            child = self.crossover(p1, p2)
            child = self.mutate(child)
            offspring.append(child)

        self.population = offspring
        self.generation += 1

        logger.info(
            f"NSGA-III Gen {self.generation}: "
            f"Pop={len(self.population)} Pareto={pareto_size}"
        )

    def train(self, objective_fn: Callable[[np.ndarray], np.ndarray], n_generations: int = 100) -> List[NSGA3Individual]:
        """Train for multiple generations."""
        if not self.population:
            self.initialize_population(genome_size=10)

        for _ in range(n_generations):
            self.evolve_generation(objective_fn)

        # Return Pareto front
        return [ind for ind in self.population if ind.rank == 0]

    def get_pareto_front(self) -> List[NSGA3Individual]:
        """Get the current Pareto front."""
        return [ind for ind in self.population if ind.rank == 0]

    def get_stats(self) -> Dict[str, Any]:
        pareto = self.get_pareto_front()
        return {
            "generation": self.generation,
            "population_size": len(self.population),
            "pareto_front_size": len(pareto),
            "n_objectives": self.config.n_objectives,
            "n_reference_points": len(self.reference_points),
        }

