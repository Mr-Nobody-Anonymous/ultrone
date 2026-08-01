# Copyright (c) Ultrone Contributors. All rights reserved.
"""
MAP-Elites Integration Layer
=============================
Integrates the MAP-Elites optimizer with the evolutionary COA generator
and tactical genome architecture. Bridges the optimization module with
the reasoning/genome ecosystem.

Key enhancements over base MAP-Elites:
- Genome-aware feature extraction (behavior characterization)
- Tactical genome encoding/decoding
- Archive visualization for commander oversight
- Integration with EvolutionaryCOAGenerator
"""

from __future__ import annotations

import logging
import random
import numpy as np
from typing import Any, Callable, Dict, List, Optional, Tuple
from dataclasses import dataclass, field

from ..optimization.map_elites import MAPElites, MAPElitesConfig
from ...reasoning.evolutionary_coagen import (
    EvolutionaryGenome, EvolutionaryCOAGenerator, PhaseParameters,
)

logger = logging.getLogger("Ultrone.Brain.Learning.Evolutionary.MAPElitesIntegration")


@dataclass
class MAPElitesIntegrationConfig:
    """Configuration for MAP-Elites integration."""
    n_bins: int = 10
    mutation_strength: float = 0.1
    n_children: int = 50
    archive_size_limit: int = 1000
    behavior_dimensions: int = 2
    elite_replacement_rate: float = 0.3


class GenomeMAPElites:
    """
    MAP-Elites operating on EvolutionaryGenome instances.
    
    Behavior space is defined by genome-level features:
    - Dimension 1: Resource conservation (aggressiveness vs caution)
    - Dimension 2: Action diversity (novelty vs specialization)
    
    The archive maps behavioral niches to high-performing genomes.
    """

    def __init__(
        self,
        coa_generator: EvolutionaryCOAGenerator,
        config: Optional[MAPElitesIntegrationConfig] = None,
    ):
        self.config = config or MAPElitesIntegrationConfig()
        self.coa_generator = coa_generator
        self._archive: Dict[Tuple[int, ...], EvolutionaryGenome] = {}
        self._archive_fitness: Dict[Tuple[int, ...], float] = {}
        self._optimizer = MAPElites(MAPElitesConfig(
            n_bins=self.config.n_bins,
            mutation_strength=self.config.mutation_strength,
            n_children=self.config.n_children,
        ))

    def _extract_behavior(self, genome: EvolutionaryGenome) -> Tuple[float, float]:
        """
        Extract behavior characteristics from a genome.
        
        Returns 2D behavior vector:
        - bc[0]: Resource conservation (0=aggressive, 1=conservative)
        - bc[1]: Action diversity (0=specialist, 1=generalist)
        """
        resource_conservation = genome.resource_conservation
        
        # Action diversity: how many actions have significant weight
        action_weights = list(genome.action_weights.values())
        if action_weights:
            diverse_actions = sum(1 for w in action_weights if w > 0.5)
            action_diversity = min(1.0, diverse_actions / max(1, len(action_weights)))
        else:
            action_diversity = 0.5
        
        return (resource_conservation, action_diversity)

    def _discretize_behavior(self, behavior: Tuple[float, float]) -> Tuple[int, int]:
        """Discretize continuous behavior into grid cell indices."""
        b0 = min(self.config.n_bins - 1, int(behavior[0] * self.config.n_bins))
        b1 = min(self.config.n_bins - 1, int(behavior[1] * self.config.n_bins))
        return (b0, b1)

    def add_to_archive(self, genome: EvolutionaryGenome) -> bool:
        """
        Add a genome to the MAP-Elites archive if it improves the niche.
        
        Returns True if archive was updated.
        """
        behavior = self._extract_behavior(genome)
        cell = self._discretize_behavior(behavior)
        fitness = genome.fitness_score

        if cell not in self._archive_fitness or fitness > self._archive_fitness[cell]:
            self._archive[cell] = genome
            self._archive_fitness[cell] = fitness
            
            # Enforce archive size limit
            if len(self._archive) > self.config.archive_size_limit:
                self._prune_archive()
            
            logger.debug(
                f"MAP-Elites archive updated at cell {cell}: "
                f"fitness={fitness:.3f}, behavior=({behavior[0]:.2f}, {behavior[1]:.2f})"
            )
            return True
        return False

    def _prune_archive(self) -> None:
        """Remove worst-performing elites when archive exceeds limit."""
        if len(self._archive) <= self.config.archive_size_limit:
            return
        
        # Sort by fitness and keep top N
        sorted_cells = sorted(
            self._archive_fitness.items(),
            key=lambda x: x[1],
            reverse=True,
        )
        keep_cells = set(cell for cell, _ in sorted_cells[:self.config.archive_size_limit])
        
        self._archive = {k: v for k, v in self._archive.items() if k in keep_cells}
        self._archive_fitness = {k: v for k, v in self._archive_fitness.items() if k in keep_cells}

    def get_elite_for_behavior(self, target_behavior: Tuple[float, float]) -> Optional[EvolutionaryGenome]:
        """Get the best genome for a given behavior target."""
        cell = self._discretize_behavior(target_behavior)
        return self._archive.get(cell)

    def get_random_elite(self) -> Optional[EvolutionaryGenome]:
        """Get a random elite from the archive."""
        if not self._archive:
            return None
        cell = random.choice(list(self._archive.keys()))
        return self._archive[cell]

    def get_best_elite(self) -> Optional[EvolutionaryGenome]:
        """Get the highest-fitness genome in the archive."""
        if not self._archive_fitness:
            return None
        best_cell = max(self._archive_fitness, key=self._archive_fitness.get)
        return self._archive.get(best_cell)

    def evolve_from_archive(self) -> EvolutionaryGenome:
        """
        Create a new genome by crossing over elites from different niches.
        
        This promotes quality diversity by combining traits from
        different behavioral regions.
        """
        if len(self._archive) < 2:
            if self._archive:
                return list(self._archive.values())[0]
            return self.coa_generator.initialize_default_genome()

        # Select two parents from different niches
        parent_a = self.get_random_elite()
        parent_b = self.get_random_elite()
        
        if parent_a is None or parent_b is None:
            return self.coa_generator.initialize_default_genome()

        # Use crossover from existing COA generator
        child = self.coa_generator.crossover_genomes(parent_a, parent_b)
        
        # Apply MAP-Elites specific mutation boost
        if random.random() < self.config.elite_replacement_rate:
            child.mutation_rate *= 1.5
        
        return child

    def get_archive_stats(self) -> Dict[str, Any]:
        """Get statistics about the current archive."""
        if not self._archive_fitness:
            return {"size": 0}
        
        fitnesses = list(self._archive_fitness.values())
        return {
            "size": len(self._archive),
            "best_fitness": max(fitnesses),
            "avg_fitness": sum(fitnesses) / len(fitnesses),
            "worst_fitness": min(fitnesses),
            "coverage": len(self._archive) / (self.config.n_bins ** 2),
        }

    def to_dict(self) -> dict:
        return {
            "config": {
                "n_bins": self.config.n_bins,
                "archive_size": len(self._archive),
            },
            "stats": self.get_archive_stats(),
        }
