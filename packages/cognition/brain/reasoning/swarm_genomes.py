# Copyright (c) Ultrone Contributors. All rights reserved.
"""Swarm genomes - CommanderGenome, AssetMicroGenome, RedForceGenome, and CoevolutionEngine."""

from __future__ import annotations

import random
import logging
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field

from .evolutionary_coagen import EvolutionaryGenome, PhaseParameters

logger = logging.getLogger("Ultrone.Brain.Reasoning.SwarmGenomes")


@dataclass
class AssetMicroGenome:
    """Micro-genome for individual swarm asset behavior."""
    asset_type: str
    aggressiveness: float = 0.5
    spacing_preference: float = 50.0
    engagement_range: float = 30.0
    responsiveness: float = 1.0
    ammo_conservation: float = 0.7

    def mutate(self, rate: float = 0.15) -> None:
        if random.random() < rate:
            self.aggressiveness = max(0.0, min(1.0, self.aggressiveness + random.gauss(0, 0.1)))
        if random.random() < rate:
            self.spacing_preference = max(10.0, min(200.0, self.spacing_preference + random.gauss(0, 10)))
        if random.random() < rate:
            self.engagement_range = max(5.0, min(100.0, self.engagement_range + random.gauss(0, 5)))
        if random.random() < rate:
            self.responsiveness = max(0.1, min(2.0, self.responsiveness + random.gauss(0, 0.1)))
        if random.random() < rate:
            self.ammo_conservation = max(0.0, min(1.0, self.ammo_conservation + random.gauss(0, 0.1)))

    def to_dict(self) -> dict:
        return {
            "asset_type": self.asset_type,
            "aggressiveness": self.aggressiveness,
            "spacing_preference": self.spacing_preference,
            "engagement_range": self.engagement_range,
            "responsiveness": self.responsiveness,
            "ammo_conservation": self.ammo_conservation,
        }


@dataclass
class CommanderGenome(EvolutionaryGenome):
    """
    Commander-level genome that spawns asset micro-genomes and coordinates swarm behavior.
    
    Extends EvolutionaryGenome with:
    - allocation_weights: how to distribute assets across domains
    - swarm_templates: pre-defined swarm micro-genome patterns
    """
    allocation_weights: Dict[str, float] = field(default_factory=lambda: {
        "drones": 0.3, "jammers": 0.2, "missiles": 0.3, "fighters": 0.2,
    })
    swarm_templates: Dict[str, List[AssetMicroGenome]] = field(default_factory=dict)

    def spawn_asset_micro_genomes(self) -> List[AssetMicroGenome]:
        """Spawn a fleet of micro-genomes based on allocation weights."""
        fleet: List[AssetMicroGenome] = []
        
        for asset_type, weight in self.allocation_weights.items():
            count = max(1, int(weight * 5))
            for i in range(count):
                micro = AssetMicroGenome(
                    asset_type=asset_type,
                    aggressiveness=random.uniform(0.3, 0.9),
                    spacing_preference=random.uniform(20, 100),
                    engagement_range=random.uniform(15, 50),
                )
                fleet.append(micro)
        
        return fleet

    def to_dict(self) -> dict:
        base = super().to_dict()
        base.update({
            "allocation_weights": self.allocation_weights,
            "swarm_templates": {k: [m.to_dict() for m in v] for k, v in self.swarm_templates.items()},
        })
        return base


@dataclass
class RedForceGenome:
    """Genome encoding Red Force evasion and ECM behavior."""
    genome_id: str
    generation: int = 0
    mutation_rate: float = 0.15
    evade_threshold: float = 0.5
    ecm_trigger_threshold: float = 0.6
    ecm_noise_level: float = 0.3
    fitness_score: float = 0.5
    fitness_history: List[float] = field(default_factory=list)

    def should_evade(self) -> bool:
        """Determine if Red Force should evade based on genome parameters."""
        return random.random() < self.evade_threshold

    def should_trigger_ecm(self) -> bool:
        """Determine if Red Force should trigger ECM."""
        return random.random() < self.ecm_trigger_threshold

    def mutate(self) -> None:
        """Mutate Red Force genome parameters."""
        if random.random() < self.mutation_rate:
            self.evade_threshold = max(0.0, min(1.0, self.evade_threshold + random.gauss(0, 0.1)))
        if random.random() < self.mutation_rate:
            self.ecm_trigger_threshold = max(0.0, min(1.0, self.ecm_trigger_threshold + random.gauss(0, 0.1)))
        if random.random() < self.mutation_rate:
            self.ecm_noise_level = max(0.0, min(1.0, self.ecm_noise_level + random.gauss(0, 0.05)))

    def to_dict(self) -> dict:
        return {
            "genome_id": self.genome_id,
            "generation": self.generation,
            "mutation_rate": self.mutation_rate,
            "evade_threshold": self.evade_threshold,
            "ecm_trigger_threshold": self.ecm_trigger_threshold,
            "ecm_noise_level": self.ecm_noise_level,
            "fitness_score": self.fitness_score,
        }


class CoevolutionEngine:
    """
    Manages co-evolution of Blue and Red genomes.
    
    Blue evolves to improve kill rates; Red evolves to improve survival.
    """
    
    def __init__(self, sample_size: int = 3):
        self.sample_size = sample_size
        self.blue_active: Optional[CommanderGenome] = None
        self.red_active: Optional[RedForceGenome] = None
        self.blue_population: List[CommanderGenome] = []
        self.red_population: List[RedForceGenome] = []
        self.blue_fitness_history: List[float] = []
        self.red_fitness_history: List[float] = []
        self.red_mutation_rate: float = 0.15

    def initialize_blue(self, genome: CommanderGenome) -> None:
        """Initialize Blue population with a genome."""
        self.blue_active = genome
        self.blue_population = [genome]
        logger.info(f"Coevolution: Blue initialized with {genome.genome_id}")

    def initialize_red(self, genome: RedForceGenome) -> None:
        """Initialize Red population with a genome."""
        self.red_active = genome
        self.red_population = [genome]
        logger.info(f"Coevolution: Red initialized with {genome.genome_id}")

    def evaluate_blue_fitness(
        self,
        blue: CommanderGenome,
        red_population: List[RedForceGenome],
        red_telemetry: Dict[str, Dict[str, Any]],
        directive: Optional[Dict[str, float]] = None,
    ) -> float:
        """Evaluate Blue genome fitness against Red population."""
        if not red_telemetry:
            blue.fitness_score = 0.5
            return 0.5
        
        avg_success = 0.0
        count = 0
        for red_id, telemetry in red_telemetry.items():
            red_survived = telemetry.get("red_survived", True)
            hits = telemetry.get("hits", 0)
            attempts = telemetry.get("attempts", 1)
            
            if not red_survived:
                avg_success += 1.0
            else:
                avg_success += hits / max(1, attempts)
            count += 1
        
        base_fitness = avg_success / max(1, count) if count > 0 else 0.5
        
        # Apply directive weights
        if directive:
            effectiveness_w = directive.get("effectiveness_weight", 0.5)
            novelty_w = directive.get("novelty_weight", 0.2)
            efficiency_w = directive.get("efficiency_weight", 0.3)
            
            novelty = getattr(blue, 'fitness_score', 0.5)
            efficiency = 1.0 - getattr(blue, 'resource_conservation', 0.7)
            
            blue.fitness_score = (
                effectiveness_w * base_fitness +
                novelty_w * novelty +
                efficiency_w * efficiency
            )
        else:
            blue.fitness_score = base_fitness
        
        blue.fitness_history.append(blue.fitness_score)
        self.blue_fitness_history.append(blue.fitness_score)
        return blue.fitness_score

    def evaluate_red_fitness(
        self,
        red: RedForceGenome,
        survived: bool,
        ecm_used: bool,
        steps_taken: int,
    ) -> float:
        """Evaluate Red genome fitness based on survival."""
        survival_score = 1.0 if survived else 0.0
        ecm_bonus = 0.2 if ecm_used else 0.0
        time_bonus = min(0.3, steps_taken / 200.0 * 0.3)
        
        red.fitness_score = min(1.0, survival_score + ecm_bonus + time_bonus)
        red.fitness_history.append(red.fitness_score)
        self.red_fitness_history.append(red.fitness_score)
        return red.fitness_score

    def evolve_blue_generation(self) -> Optional[CommanderGenome]:
        """Evolve Blue population to next generation."""
        if not self.blue_population:
            return None
        
        # Sort by fitness
        self.blue_population.sort(key=lambda g: g.fitness_score, reverse=True)
        
        # Keep top half
        survivors = self.blue_population[:max(1, len(self.blue_population) // 2)]
        
        # Elitism - keep best
        best = survivors[0]
        
        # Generate offspring
        offspring: List[CommanderGenome] = []
        target_size = len(self.blue_population)
        while len(survivors) + len(offspring) < target_size:
            parent = random.choice(survivors)
            child = CommanderGenome(
                genome_id=f"BLUE-{random.randint(10000, 99999)}",
                generation=parent.generation + 1,
                agent_id=parent.agent_id,
                action_weights=dict(parent.action_weights),
                synergy_map=dict(parent.synergy_map),
                phase_params={k: PhaseParameters(**v.__dict__) for k, v in parent.phase_params.items()},
                resource_conservation=parent.resource_conservation,
                time_optimization=parent.time_optimization,
                domain=parent.domain,
                mutation_rate=parent.mutation_rate,
                allocation_weights=dict(parent.allocation_weights),
            )
            # Mutate
            if random.random() < child.mutation_rate:
                for action in child.action_weights:
                    child.action_weights[action] = max(0.0, min(1.0,
                        child.action_weights[action] + random.gauss(0, 0.15)))
            offspring.append(child)
        
        self.blue_population = survivors + offspring
        self.blue_active = self.blue_population[0]
        logger.info(f"Blue evolved: gen={self.blue_active.generation}, fitness={self.blue_active.fitness_score:.3f}")
        return self.blue_active

    def evolve_red_generation(self) -> Optional[RedForceGenome]:
        """Evolve Red population to next generation."""
        if not self.red_population:
            return None
        
        self.red_population.sort(key=lambda g: g.fitness_score, reverse=True)
        survivors = self.red_population[:max(1, len(self.red_population) // 2)]
        
        offspring: List[RedForceGenome] = []
        target_size = len(self.red_population)
        while len(survivors) + len(offspring) < target_size:
            parent = random.choice(survivors)
            child = RedForceGenome(
                genome_id=f"RED-{random.randint(10000, 99999)}",
                generation=parent.generation + 1,
                mutation_rate=self.red_mutation_rate,
                evade_threshold=parent.evade_threshold,
                ecm_trigger_threshold=parent.ecm_trigger_threshold,
                ecm_noise_level=parent.ecm_noise_level,
            )
            child.mutate()
            offspring.append(child)
        
        self.red_population = survivors + offspring
        self.red_active = self.red_population[0]
        logger.info(f"Red evolved: gen={self.red_active.generation}, fitness={self.red_active.fitness_score:.3f}")
        return self.red_active

    def get_stats(self) -> dict:
        return {
            "blue_population_size": len(self.blue_population),
            "red_population_size": len(self.red_population),
            "blue_fitness": self.blue_active.fitness_score if self.blue_active else 0,
            "red_fitness": self.red_active.fitness_score if self.red_active else 0,
            "blue_generation": self.blue_active.generation if self.blue_active else 0,
            "red_generation": self.red_active.generation if self.red_active else 0,
            "red_mutation_rate": self.red_mutation_rate,
        }

