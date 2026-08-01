"""
Epigenetic / Lamarckian Evolution
==================================
Implements epigenetic inheritance mechanisms where learned traits
can be passed to offspring, inspired by Lamarckian evolution and
epigenetic regulation.

Key concepts:
1. Epigenetic Tags: Markers on genes that modify expression without changing DNA
2. Lamarckian Inheritance: Learned behaviors can be inherited
3. Epigenetic Regulation: Experienced-based gene expression modification
4. Transgenerational Epigenetic Inheritance: Traits passed across generations

This allows the system to inherit learned adaptations, not just genetic mutations.
"""

from __future__ import annotations

import logging
import random
import copy
from typing import Dict, List, Optional, Tuple, Callable, Any, Set
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger("Ultrone.Brain.Learning.Evolutionary.Epigenetic")


class EpigeneticMark(Enum):
    """Types of epigenetic marks that can modify gene expression."""
    METHYLATION = "methylation"       # Silences gene expression
    ACETYLATION = "acetylation"       # Enhances gene expression
    PHOSPHORYLATION = "phosphorylation"  # Activates/inactivates
    UBIQUITINATION = "ubiquitination"  # Marks for degradation
    SUMOYLATION = "sumoylation"       # Modifies protein interactions


@dataclass
class EpigeneticTag:
    """An epigenetic mark on a gene that modifies its expression."""
    gene_name: str
    mark_type: EpigeneticMark = EpigeneticMark.METHYLATION
    strength: float = 0.5  # 0.0 = no effect, 1.0 = full effect
    heritability: float = 0.7  # Probability of passing to offspring
    environment_triggered: bool = False  # Whether this was learned from environment

    def modify_expression(self, base_value: float) -> float:
        """Apply epigenetic modification to a gene's expression."""
        if self.mark_type == EpigeneticMark.METHYLATION:
            return base_value * (1.0 - self.strength * 0.5)
        elif self.mark_type == EpigeneticMark.ACETYLATION:
            return base_value * (1.0 + self.strength * 0.3)
        elif self.mark_type == EpigeneticMark.PHOSPHORYLATION:
            return base_value * (1.0 + self.strength * 0.2)
        elif self.mark_type == EpigeneticMark.UBIQUITINATION:
            return base_value * (1.0 - self.strength * 0.7)
        elif self.mark_type == EpigeneticMark.SUMOYLATION:
            return base_value * (1.0 + self.strength * 0.15)
        return base_value

    def clone(self) -> EpigeneticTag:
        return EpigeneticTag(
            gene_name=self.gene_name,
            mark_type=self.mark_type,
            strength=self.strength,
            heritability=self.heritability,
            environment_triggered=self.environment_triggered,
        )


@dataclass
class EpigeneticState:
    """
    The epigenetic state of an individual, containing all marks.
    """
    epigenome_id: str
    tags: Dict[str, List[EpigeneticTag]] = field(default_factory=dict)
    learned_parameters: Dict[str, float] = field(default_factory=dict)
    experience_buffer: List[Dict[str, Any]] = field(default_factory=list)

    def add_tag(self, tag: EpigeneticTag) -> None:
        if tag.gene_name not in self.tags:
            self.tags[tag.gene_name] = []
        self.tags[tag.gene_name].append(tag)

    def get_expression_modification(self, gene_name: str) -> float:
        """Get the combined expression modification factor for a gene."""
        factor = 1.0
        for tag in self.tags.get(gene_name, []):
            factor *= tag.modify_expression(1.0)
        return factor

    def record_learning(self, parameter_name: str, value: float) -> None:
        """Record a learned parameter value that may be inherited."""
        self.learned_parameters[parameter_name] = value

    def clone(self, new_id: str) -> EpigeneticState:
        """Clone epigenetic state with heritability filtering."""
        new_state = EpigeneticState(epigenome_id=new_id)

        # Inherit tags based on heritability
        for gene_name, tags in self.tags.items():
            for tag in tags:
                if random.random() < tag.heritability:
                    new_state.add_tag(tag.clone())

        # Inherit learned parameters (Lamarckian inheritance)
        for param_name, value in self.learned_parameters.items():
            # Add some noise to inherited parameters
            inherited_value = value + random.gauss(0, 0.05)
            new_state.learned_parameters[param_name] = max(0.0, min(1.0, inherited_value))

        return new_state


@dataclass
class EpigeneticConfig:
    """Configuration for epigenetic evolution."""
    population_size: int = 50
    mutation_rate: float = 0.15
    epigenetic_mutation_rate: float = 0.1
    crossover_rate: float = 0.7
    lamarckian_inheritance_rate: float = 0.5  # How much learned info is inherited
    max_tags_per_gene: int = 3
    n_elites: int = 5
    experience_window: int = 10


class EpigeneticGenome:
    """
    A genome with epigenetic state that can inherit learned traits.

    Combines base genetic parameters with epigenetic modifications
    and experience-based learning.
    """

    def __init__(self, genome_id: str, parameters: Optional[Dict[str, float]] = None):
        self.genome_id = genome_id
        self.parameters: Dict[str, float] = parameters or {}
        self.epigenetic_state = EpigeneticState(f"epi_{genome_id}")
        self.fitness: float = 0.0
        self.generation: int = 0
        self._expressed_parameters: Dict[str, float] = {}

    def get_expressed(self, param_name: str) -> float:
        """Get the expressed value of a parameter (after epigenetic modification)."""
        base = self.parameters.get(param_name, 0.5)
        epi_factor = self.epigenetic_state.get_expression_modification(param_name)
        learned = self.epigenetic_state.learned_parameters.get(param_name, 0.0)

        # Combine base + epigenetic + learned
        expressed = base * epi_factor
        if learned > 0:
            expressed = expressed * (1.0 - 0.3) + learned * 0.3

        self._expressed_parameters[param_name] = expressed
        return expressed

    def learn(self, param_name: str, new_value: float) -> None:
        """Learn a new parameter value from experience."""
        self.epigenetic_state.record_learning(param_name, new_value)

        # Add epigenetic tag if learning is significant
        if random.random() < 0.1:
            tag = EpigeneticTag(
                gene_name=param_name,
                mark_type=random.choice(list(EpigeneticMark)),
                strength=random.uniform(0.2, 0.8),
                environment_triggered=True,
            )
            self.epigenetic_state.add_tag(tag)

    def mutate(self, mutation_rate: float) -> None:
        """Mutate genetic parameters."""
        for key in self.parameters:
            if random.random() < mutation_rate:
                self.parameters[key] += random.gauss(0, 0.1)
                self.parameters[key] = max(0.0, min(1.0, self.parameters[key]))

    def clone(self, new_id: Optional[str] = None) -> EpigeneticGenome:
        """Clone with epigenetic inheritance."""
        child = EpigeneticGenome(
            genome_id=new_id or f"{self.genome_id}_clone",
            parameters=dict(self.parameters),
        )
        # Epigenetic state inheritance (Lamarckian)
        child.epigenetic_state = self.epigenetic_state.clone(f"epi_{child.genome_id}")
        child.generation = self.generation + 1
        return child

    def clone_without_epigenetics(self, new_id: str) -> EpigeneticGenome:
        """Clone without epigenetic inheritance (pure Darwinian)."""
        return EpigeneticGenome(
            genome_id=new_id,
            parameters=dict(self.parameters),
        )


class EpigeneticEvolution:
    """
    Epigenetic / Lamarckian Evolution Engine.

    Evolves a population of genomes that can inherit learned traits
    through epigenetic marks and Lamarckian inheritance.

    This bridges the gap between evolution (slow) and learning (fast),
    allowing the system to accumulate both genetic and experiential knowledge.
    """

    def __init__(self, config: Optional[EpigeneticConfig] = None):
        self.config = config or EpigeneticConfig()
        self.population: List[EpigeneticGenome] = []
        self.generation = 0
        self.best_genome: Optional[EpigeneticGenome] = None
        self.best_fitness: float = 0.0
        self._fitness_history: List[float] = []

    def initialize_population(self, n_params: int = 5) -> None:
        """Initialize population with random genomes."""
        self.population = []
        for i in range(self.config.population_size):
            params = {f"param_{j}": random.uniform(0.0, 1.0) for j in range(n_params)}
            genome = EpigeneticGenome(genome_id=f"EPI-{i}", parameters=params)
            self.population.append(genome)

    def evaluate_population(self, fitness_fn: Callable[[EpigeneticGenome], float]) -> None:
        """Evaluate all genomes and track best."""
        for genome in self.population:
            genome.fitness = fitness_fn(genome)
            if genome.fitness > self.best_fitness:
                self.best_fitness = genome.fitness
                self.best_genome = genome.clone()

    def select_elites(self) -> List[EpigeneticGenome]:
        """Select top-performing individuals."""
        scored = sorted(self.population, key=lambda g: g.fitness, reverse=True)
        return [g.clone(f"ELITE-{random.randint(10000, 99999)}") for g in scored[:self.config.n_elites]]

    def crossover(self, p1: EpigeneticGenome, p2: EpigeneticGenome) -> EpigeneticGenome:
        """Blend crossover with epigenetic blending."""
        all_keys = set(p1.parameters.keys()) | set(p2.parameters.keys())
        params = {}
        for key in all_keys:
            v1 = p1.parameters.get(key, 0.5)
            v2 = p2.parameters.get(key, 0.5)
            alpha = random.uniform(0.3, 0.7)
            params[key] = alpha * v1 + (1.0 - alpha) * v2

        child = EpigeneticGenome(
            genome_id=f"CROSS-{random.randint(10000, 99999)}",
            parameters=params,
        )
        child.generation = max(p1.generation, p2.generation) + 1

        # Inherit epigenetic state from both parents
        for gene_name, tags in p1.epigenetic_state.tags.items():
            for tag in tags:
                if random.random() < tag.heritability * 0.5:
                    child.epigenetic_state.add_tag(tag.clone())

        return child

    def evolve_generation(self, fitness_fn: Callable[[EpigeneticGenome], float]) -> None:
        """Run one generation of epigenetic evolution."""
        self.evaluate_population(fitness_fn)

        avg_fitness = sum(g.fitness for g in self.population) / len(self.population)
        self._fitness_history.append(avg_fitness)

        # Elitism
        elites = self.select_elites()

        # Reproduce
        offspring = list(elites)
        while len(offspring) < self.config.population_size:
            if random.random() < self.config.crossover_rate and len(elites) >= 2:
                p1 = random.choice(elites)
                p2 = random.choice([g for g in elites if g.genome_id != p1.genome_id])
                child = self.crossover(p1, p2)
            else:
                parent = random.choice(elites)

                # Lamarckian inheritance: learned traits are inherited
                if random.random() < self.config.lamarckian_inheritance_rate:
                    child = parent.clone(f"LAM-{random.randint(10000, 99999)}")
                else:
                    child = parent.clone_without_epigenetics(f"DAR-{random.randint(10000, 99999)}")

            child.mutate(self.config.mutation_rate)
            offspring.append(child)

        self.population = offspring[:self.config.population_size]
        self.generation += 1

        logger.info(
            f"Epigenetic Gen {self.generation}: "
            f"Best={self.best_fitness:.4f} Avg={avg_fitness:.4f}"
        )

    def train(self, fitness_fn: Callable[[EpigeneticGenome], float], n_generations: int = 100) -> EpigeneticGenome:
        """Train for multiple generations."""
        if not self.population:
            self.initialize_population()

        for _ in range(n_generations):
            self.evolve_generation(fitness_fn)

        return self.best_genome if self.best_genome else self.population[0]

    def get_stats(self) -> Dict[str, Any]:
        avg_epigenetic_tags = sum(
            sum(len(tags) for tags in g.epigenetic_state.tags.values())
            for g in self.population
        ) / max(1, len(self.population))

        return {
            "generation": self.generation,
            "population_size": len(self.population),
            "best_fitness": self.best_fitness,
            "avg_fitness": (sum(self._fitness_history) / len(self._fitness_history))
                if self._fitness_history else 0.0,
            "avg_epigenetic_tags": avg_epigenetic_tags,
            "lamarckian_inheritance_rate": self.config.lamarckian_inheritance_rate,
        }

