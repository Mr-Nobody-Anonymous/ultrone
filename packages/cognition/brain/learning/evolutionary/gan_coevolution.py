"""
GAN Coevolution
===============
Generative Adversarial Co-evolution framework.

Extends the Red/Blue coevolution concept with GAN-style training:
- Blue forces act as the "Generator" (trying to generate winning tactics)
- Red forces act as the "Discriminator" (trying to survive/detect Blue tactics)
- Creates an adversarial arms race that continuously improves both sides

This is the evolutionary equivalent of GANs - instead of backprop,
we use evolutionary pressure to drive improvement.
"""

from __future__ import annotations

import logging
import random
import numpy as np
from typing import Dict, List, Optional, Tuple, Callable, Any
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger("Ultrone.Brain.Learning.Evolutionary.GANCoevolution")


class AdversarialPhase(Enum):
    """Phases of adversarial co-evolution training."""
    BLUE_ATTACK = "blue_attack"       # Blue evolves to defeat current Red
    RED_DEFEND = "red_defend"         # Red evolves to counter current Blue
    ADVERSARIAL = "adversarial"       # Both evolve simultaneously
    CURRICULUM = "curriculum"         # Progressive difficulty scaling


@dataclass
class GANCoevolutionConfig:
    """Configuration for GAN-style co-evolution."""
    blue_population_size: int = 50
    red_population_size: int = 50
    blue_mutation_rate: float = 0.15
    red_mutation_rate: float = 0.15
    crossover_rate: float = 0.7
    elitism_ratio: float = 0.1
    n_generations_per_phase: int = 10
    adversarial_generations: int = 100
    curriculum_levels: int = 5
    fitness_threshold: float = 0.6  # Threshold for switching phases
    archive_size: int = 100  # Store past Red defenses to prevent overfitting


@dataclass
class AdversarialGenome:
    """A genome in the adversarial co-evolution system."""
    genome_id: str
    parameters: Dict[str, float] = field(default_factory=dict)
    fitness: float = 0.0
    generation: int = 0
    wins: int = 0
    losses: int = 0
    domain: str = "all"

    def win_rate(self) -> float:
        total = self.wins + self.losses
        return self.wins / max(1, total)

    def clone(self, new_id: Optional[str] = None) -> AdversarialGenome:
        return AdversarialGenome(
            genome_id=new_id or f"{self.genome_id}_clone",
            parameters=dict(self.parameters),
            fitness=self.fitness,
            generation=self.generation + 1,
            wins=self.wins,
            losses=self.losses,
            domain=self.domain,
        )

    def mutate(self, mutation_rate: float = 0.15) -> None:
        """Mutate parameters."""
        for key in self.parameters:
            if random.random() < mutation_rate:
                self.parameters[key] += random.gauss(0, 0.1)
                self.parameters[key] = max(0.0, min(1.0, self.parameters[key]))


class GANCoevolution:
    """
    GAN-style Co-evolution of Blue (generator) and Red (discriminator) forces.

    Blue evolves to generate effective tactics against Red.
    Red evolves to defend against Blue's tactics.
    Both improve through adversarial pressure.
    """

    def __init__(self, config: Optional[GANCoevolutionConfig] = None):
        self.config = config or GANCoevolutionConfig()
        self.phase = AdversarialPhase.BLUE_ATTACK
        self.generation = 0
        self.curriculum_level = 0

        # Blue population (attacker/generator)
        self.blue_population: List[AdversarialGenome] = []
        self.best_blue: Optional[AdversarialGenome] = None
        self.best_blue_fitness: float = 0.0

        # Red population (defender/discriminator)
        self.red_population: List[AdversarialGenome] = []
        self.best_red: Optional[AdversarialGenome] = None
        self.best_red_fitness: float = 0.0

        # Archive of past Red defenses
        self.red_archive: List[AdversarialGenome] = []

        self._blue_fitness_history: List[float] = []
        self._red_fitness_history: List[float] = []

    def initialize_populations(self, n_params: int = 5) -> None:
        """Initialize both populations with random genomes."""
        self.blue_population = []
        self.red_population = []

        for i in range(self.config.blue_population_size):
            genome = AdversarialGenome(
                genome_id=f"BLUE-{i}",
                parameters={f"param_{j}": random.uniform(0.0, 1.0) for j in range(n_params)},
            )
            self.blue_population.append(genome)

        for i in range(self.config.red_population_size):
            genome = AdversarialGenome(
                genome_id=f"RED-{i}",
                parameters={f"param_{j}": random.uniform(0.0, 1.0) for j in range(n_params)},
            )
            self.red_population.append(genome)

        self.best_blue = self.blue_population[0]
        self.best_red = self.red_population[0]

    def evaluate_blue_fitness(
        self,
        blue_genome: AdversarialGenome,
        red_population: List[AdversarialGenome],
        sim_fn: Callable[[AdversarialGenome, AdversarialGenome], float],
    ) -> float:
        """
        Evaluate Blue fitness by pitting it against Red opponents.

        Blue gets higher fitness for defeating Red.
        Uses curriculum level to scale difficulty.
        """
        scores = []
        n_opponents = max(1, min(5, len(red_population)))

        opponents = random.sample(red_population, n_opponents)
        for red in opponents:
            score = sim_fn(blue_genome, red)
            scores.append(score)

        avg_score = sum(scores) / len(scores)

        # Curriculum scaling: higher levels require higher scores
        curriculum_bonus = 1.0 + self.curriculum_level * 0.1
        adjusted_score = avg_score * curriculum_bonus

        blue_genome.fitness = min(1.0, adjusted_score)
        if avg_score > 0.5:
            blue_genome.wins += 1
        else:
            blue_genome.losses += 1

        return blue_genome.fitness

    def evaluate_red_fitness(
        self,
        red_genome: AdversarialGenome,
        blue_population: List[AdversarialGenome],
        sim_fn: Callable[[AdversarialGenome, AdversarialGenome], float],
    ) -> float:
        """
        Evaluate Red fitness by defending against Blue attacks.

        Red gets higher fitness for surviving Blue attacks.
        """
        scores = []
        n_attackers = max(1, min(5, len(blue_population)))

        attackers = random.sample(blue_population, n_attackers)
        for blue in attackers:
            score = 1.0 - sim_fn(blue, red_genome)  # Red wants low blue score
            scores.append(score)

        avg_score = sum(scores) / len(scores)

        red_genome.fitness = min(1.0, avg_score)
        if avg_score > 0.5:
            red_genome.wins += 1
        else:
            red_genome.losses += 1

        return red_genome.fitness

    def select_elites(self, population: List[AdversarialGenome], n_elite: int) -> List[AdversarialGenome]:
        """Select top individuals."""
        scored = sorted(population, key=lambda g: g.fitness, reverse=True)
        return [g.clone() for g in scored[:n_elite]]

    def crossover(self, p1: AdversarialGenome, p2: AdversarialGenome) -> AdversarialGenome:
        """Blend crossover between two genomes."""
        child = AdversarialGenome(
            genome_id=f"CROSS-{random.randint(10000, 99999)}",
            generation=max(p1.generation, p2.generation) + 1,
        )
        all_keys = set(p1.parameters.keys()) | set(p2.parameters.keys())
        for key in all_keys:
            v1 = p1.parameters.get(key, 0.5)
            v2 = p2.parameters.get(key, 0.5)
            alpha = random.uniform(0.3, 0.7)
            child.parameters[key] = alpha * v1 + (1.0 - alpha) * v2
        return child

    def reproduce_population(
        self,
        population: List[AdversarialGenome],
        target_size: int,
        mutation_rate: float,
    ) -> List[AdversarialGenome]:
        """Create next generation from current population."""
        n_elite = max(1, int(target_size * self.config.elitism_ratio))
        elites = self.select_elites(population, n_elite)

        offspring = list(elites)
        while len(offspring) < target_size:
            if random.random() < self.config.crossover_rate and len(elites) >= 2:
                p1 = random.choice(elites)
                p2 = random.choice([g for g in elites if g.genome_id != p1.genome_id])
                child = self.crossover(p1, p2)
            else:
                parent = random.choice(elites)
                child = parent.clone(f"OFF-{random.randint(10000, 99999)}")

            child.mutate(mutation_rate)
            offspring.append(child)

        return offspring[:target_size]

    def evolve_blue(self, sim_fn: Callable[[AdversarialGenome, AdversarialGenome], float]) -> None:
        """Evolve Blue population."""
        for genome in self.blue_population:
            self.evaluate_blue_fitness(genome, self.red_population, sim_fn)

        avg_fitness = sum(g.fitness for g in self.blue_population) / len(self.blue_population)
        self._blue_fitness_history.append(avg_fitness)

        # Track best
        best = max(self.blue_population, key=lambda g: g.fitness)
        if best.fitness > self.best_blue_fitness:
            self.best_blue_fitness = best.fitness
            self.best_blue = best.clone()

        self.blue_population = self.reproduce_population(
            self.blue_population,
            self.config.blue_population_size,
            self.config.blue_mutation_rate,
        )

    def evolve_red(self, sim_fn: Callable[[AdversarialGenome, AdversarialGenome], float]) -> None:
        """Evolve Red population."""
        for genome in self.red_population:
            self.evaluate_red_fitness(genome, self.blue_population, sim_fn)

        avg_fitness = sum(g.fitness for g in self.red_population) / len(self.red_population)
        self._red_fitness_history.append(avg_fitness)

        # Track best
        best = max(self.red_population, key=lambda g: g.fitness)
        if best.fitness > self.best_red_fitness:
            self.best_red_fitness = best.fitness
            self.best_red = best.clone()

        # Archive past red defenses
        if len(self.red_archive) < self.config.archive_size:
            self.red_archive.append(best.clone())

        self.red_population = self.reproduce_population(
            self.red_population,
            self.config.red_population_size,
            self.config.red_mutation_rate,
        )

    def evolve_generation(
        self,
        sim_fn: Callable[[AdversarialGenome, AdversarialGenome], float],
    ) -> None:
        """Run one generation of adversarial co-evolution."""
        if self.phase == AdversarialPhase.BLUE_ATTACK:
            self.evolve_blue(sim_fn)
            avg_blue = sum(g.fitness for g in self.blue_population) / len(self.blue_population)
            if avg_blue > self.config.fitness_threshold:
                self.phase = AdversarialPhase.RED_DEFEND
                logger.info("Switching to RED_DEFEND phase")

        elif self.phase == AdversarialPhase.RED_DEFEND:
            self.evolve_red(sim_fn)
            avg_red = sum(g.fitness for g in self.red_population) / len(self.red_population)
            if avg_red > self.config.fitness_threshold:
                self.phase = AdversarialPhase.ADVERSARIAL
                logger.info("Switching to ADVERSARIAL phase")

        elif self.phase == AdversarialPhase.ADVERSARIAL:
            self.evolve_blue(sim_fn)
            self.evolve_red(sim_fn)

        elif self.phase == AdversarialPhase.CURRICULUM:
            self.evolve_blue(sim_fn)
            self.evolve_red(sim_fn)
            # Check if should advance curriculum
            avg_blue = sum(g.fitness for g in self.blue_population) / len(self.blue_population)
            avg_red = sum(g.fitness for g in self.red_population) / len(self.red_population)
            if avg_blue > self.config.fitness_threshold and avg_red > self.config.fitness_threshold:
                self.curriculum_level = min(self.config.curriculum_levels, self.curriculum_level + 1)
                logger.info(f"Advancing to curriculum level {self.curriculum_level}")

        self.generation += 1

    def train(self, sim_fn: Callable[[AdversarialGenome, AdversarialGenome], float], n_generations: int = 100) -> None:
        """Train adversarial co-evolution."""
        if not self.blue_population:
            self.initialize_populations()

        for _ in range(n_generations):
            self.evolve_generation(sim_fn)

        logger.info(
            f"GAN Coevolution complete: {self.generation} generations. "
            f"Best Blue: {self.best_blue_fitness:.3f}, Best Red: {self.best_red_fitness:.3f}"
        )

    def get_red_archive(self) -> List[AdversarialGenome]:
        """Get the archive of past Red defenses for testing robustness."""
        return list(self.red_archive)

    def get_stats(self) -> Dict[str, Any]:
        return {
            "generation": self.generation,
            "phase": self.phase.value,
            "curriculum_level": self.curriculum_level,
            "blue_population_size": len(self.blue_population),
            "red_population_size": len(self.red_population),
            "best_blue_fitness": self.best_blue_fitness,
            "best_red_fitness": self.best_red_fitness,
            "blue_win_rate": self.best_blue.win_rate() if self.best_blue else 0.0,
            "red_win_rate": self.best_red.win_rate() if self.best_red else 0.0,
            "red_archive_size": len(self.red_archive),
        }

