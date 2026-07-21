# Copyright (c) Ultrone Contributors. All rights reserved.
"""Coevolution engine for adversarial Blue vs Red evolution."""

from __future__ import annotations

import logging
import random
from typing import Any, Dict, List, Optional, Tuple

from .evolutionary_coagen import EvolutionaryCOAGenerator, CommanderGenome
from .red_force_genomes import RedForceGenome

logger = logging.getLogger("Ultrone.Brain.Reasoning.Coevolution")


class CoevolutionEngine:
    """
    Manages two adversarial populations: Blue Commanders and Red Force genomes.
    
    Blue fitness is tested against current best Red genomes.
    Red fitness is tested against current best Blue commanders.
    This creates an endless arms race.
    """
    
    def __init__(self, sample_size: int = 3) -> None:
        self.sample_size = sample_size
        
        # Blue population: CommanderGenomes
        self.blue_population: List[CommanderGenome] = []
        self.blue_active: Optional[CommanderGenome] = None
        
        # Red population: RedForceGenomes
        self.red_population: List[RedForceGenome] = []
        self.red_active: Optional[RedForceGenome] = None
        
        # Evolution generators
        self.blue_generator = EvolutionaryCOAGenerator()
        self.red_mutation_rate = 0.15
    
    def initialize_blue(self, commander: CommanderGenome) -> None:
        """Initialize Blue population with a starting commander."""
        self.blue_population = [commander]
        self.blue_active = commander
    
    def initialize_red(self, red_genome: RedForceGenome) -> None:
        """Initialize Red population with a starting genome."""
        self.red_population = [red_genome]
        self.red_active = red_genome
    
    def evaluate_blue_fitness(self, commander: CommanderGenome,
                              red_sample: List[RedForceGenome],
                              telemetry_by_red: Dict[str, Dict[str, Any]]) -> float:
        """
        Evaluate Blue fitness by testing against a sample of Red genomes.
        
        Args:
            commander: Blue commander to evaluate
            red_sample: Sample of Red genomes to test against
            telemetry_data: Combined telemetry from battles against red_sample
            
        Returns:
            Fitness score for the Blue commander
        """
        total_fitness = 0.0
        valid_matches = 0
        
        for red_genome in red_sample:
            telemetry = telemetry_by_red.get(red_genome.genome_id, {})
            if not telemetry:
                continue
            
            # Calculate base fitness
            hits = telemetry.get("hits", 0)
            attempts = telemetry.get("attempts", 1)
            effectiveness = hits / max(1, attempts)
            
            weapons_used = telemetry.get("weapons_used", 1)
            weapons_allocated = telemetry.get("weapons_allocated", 1)
            efficiency = 1.0 - (weapons_used / max(1, weapons_allocated))
            
            actions_used = telemetry.get("actions_used", [])
            novelty = min(1.0, len(set(actions_used)) / 10)
            
            fitness = 0.5 * effectiveness + 0.3 * efficiency + 0.2 * novelty
            
            # Penalties
            if telemetry.get("blue_on_blue", 0) > 0:
                fitness *= 0.01
            elif telemetry.get("collateral", 0) > 0:
                fitness *= 0.7
            
            total_fitness += fitness
            valid_matches += 1
        
        commander.fitness_score = total_fitness / max(1, valid_matches)
        commander.fitness_history.append(commander.fitness_score)
        return commander.fitness_score
    
    def evaluate_red_fitness(self, red_genome: RedForceGenome,
                             blue_sample: List[CommanderGenome],
                             telemetry_by_blue: Dict[str, Dict[str, Any]]) -> float:
        """
        Evaluate Red fitness by testing against a sample of Blue commanders.
        
        Red fitness = survival rate + damage inflicted.
        
        Args:
            red_genome: Red genome to evaluate
            blue_sample: Sample of Blue commanders to test against
            telemetry_by_blue: Combined telemetry from battles against blue_sample
            
        Returns:
            Fitness score for the Red genome
        """
        total_survival = 0.0
        total_damage_inflicted = 0.0
        valid_matches = 0
        
        for blue_commander in blue_sample:
            telemetry = telemetry_by_blue.get(blue_commander.genome_id, {})
            if not telemetry:
                continue
            
            # Red survives if Blue never got a kill
            survived = 1.0 if telemetry.get("red_survived", True) else 0.0
            
            # Damage inflicted = Blue ammo spent / Blue ammo allocated (resource drain)
            ammo_used = telemetry.get("weapons_used", 0)
            ammo_allocated = telemetry.get("weapons_allocated", 1)
            damage_inflicted = ammo_used / max(1, ammo_allocated)
            
            survival_score = survived * 0.7 + damage_inflicted * 0.3
            
            total_survival += survival_score
            total_damage_inflicted += damage_inflicted
            valid_matches += 1
        
        red_genome.fitness_score = total_survival / max(1, valid_matches)
        red_genome.fitness_history.append(red_genome.fitness_score)
        return red_genome.fitness_score
    
    def evolve_blue_generation(self) -> Optional[CommanderGenome]:
        """Evolve Blue population one generation using commander-specific operators."""
        if len(self.blue_population) < 2:
            return None
        
        # Sort by fitness
        self.blue_population.sort(key=lambda g: g.fitness_score, reverse=True)
        survivors = self.blue_population[:max(1, len(self.blue_population) // 2)]
        
        offspring: List[CommanderGenome] = []
        while len(survivors) + len(offspring) < len(self.blue_population):
            parent_a = random.choice(survivors)
            parent_b = random.choice(survivors)
            
            if random.random() < 0.7:
                child = self.blue_generator._crossover_commanders(parent_a, parent_b)
            else:
                child = self.blue_generator._mutate_commander(parent_a)
            
            offspring.append(child)
        
        self.blue_population = survivors + offspring
        self.blue_active = self.blue_population[0]
        return self.blue_active
    
    def evolve_red_generation(self) -> Optional[RedForceGenome]:
        """Evolve Red population one generation."""
        if len(self.red_population) < 2:
            return None
        
        # Sort by fitness
        self.red_population.sort(key=lambda g: g.fitness_score, reverse=True)
        survivors = self.red_population[:max(1, len(self.red_population) // 2)]
        
        offspring: List[RedForceGenome] = []
        while len(survivors) + len(offspring) < len(self.red_population):
            parent_a = random.choice(survivors)
            parent_b = random.choice(survivors)
            
            if random.random() < 0.7:
                child = parent_a.crossover(parent_b)
            else:
                child = parent_a.mutate()
            
            offspring.append(child)
        
        self.red_population = survivors + offspring
        self.red_active = self.red_population[0]
        return self.red_active
    
    def get_blue_best(self, n: int = 1) -> List[CommanderGenome]:
        """Get top N Blue commanders by fitness."""
        sorted_blue = sorted(self.blue_population, key=lambda g: g.fitness_score, reverse=True)
        return sorted_blue[:n]
    
    def get_red_best(self, n: int = 1) -> List[RedForceGenome]:
        """Get top N Red genomes by fitness."""
        sorted_red = sorted(self.red_population, key=lambda g: g.fitness_score, reverse=True)
        return sorted_red[:n]
    
    def get_red_sample(self) -> List[RedForceGenome]:
        """Get a sample of Red genomes for Blue fitness evaluation."""
        if len(self.red_population) <= self.sample_size:
            return list(self.red_population)
        return random.sample(self.red_population, self.sample_size)
    
    def get_blue_sample(self) -> List[CommanderGenome]:
        """Get a sample of Blue commanders for Red fitness evaluation."""
        if len(self.blue_population) <= self.sample_size:
            return list(self.blue_population)
        return random.sample(self.blue_population, self.sample_size)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get coevolution statistics."""
        return {
            "blue_population_size": len(self.blue_population),
            "red_population_size": len(self.red_population),
            "blue_best_fitness": max((g.fitness_score for g in self.blue_population), default=0.0),
            "red_best_fitness": max((g.fitness_score for g in self.red_population), default=0.0),
            "blue_active_fitness": self.blue_active.fitness_score if self.blue_active else 0.0,
            "red_active_fitness": self.red_active.fitness_score if self.red_active else 0.0,
        }