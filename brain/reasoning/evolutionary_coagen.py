# Copyright (c) Ultrone Contributors. All rights reserved.
"""Evolutionary COA Generator - evolves tactical DNA using GEP."""

from __future__ import annotations

import random
import logging
from typing import Dict, List, Optional, Any, TYPE_CHECKING
from dataclasses import dataclass, field

if TYPE_CHECKING:
    from ..learning.evolution_lab import EvolutionLab
    from ...sim import WorldState
    from ...data.entities import Unit

logger = logging.getLogger("Ultrone.Brain.Reasoning.EvolutionaryCOA")


# Hardcoded ROE Rules
ROE_VIOLATION_CHECKS = [
    lambda genome, domain: "nuke" in genome.get("weapons", []) and domain != "strategic",
    lambda genome, domain: genome.get("collateral_averse", 1.0) < 0.3 and genome.get("target_type") == "civilian",
]


def violates_roe(genome: "EvolutionaryGenome", domain: str) -> bool:
    """Check if genome violates Rules of Engagement."""
    for check in ROE_VIOLATION_CHECKS:
        if check(genome, domain):
            return True
    return False


@dataclass
class PhaseParameters:
    """Parameters for a single F2T2EA phase."""
    speed: float = 1.0
    confidence_threshold: float = 0.7
    resource_efficiency: float = 0.8


@dataclass
class EvolutionaryGenome:
    """
    Tactical genome encoding COA generation strategies.
    
    Encodes how to generate and execute Courses of Action.
    """
    genome_id: str
    generation: int = 0
    agent_id: str = ""
    
    # Tactical parameters
    action_weights: Dict[str, float] = field(default_factory=dict)
    synergy_map: Dict[tuple, float] = field(default_factory=dict)
    phase_params: Dict[str, PhaseParameters] = field(default_factory=dict)
    
    # Efficiency parameters
    resource_conservation: float = 0.7
    time_optimization: float = 1.0
    
    # Evolution control
    domain: str = "all"
    mutation_rate: float = 0.15
    fitness_score: float = 0.5
    fitness_history: List[float] = field(default_factory=list)
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get gene value by key."""
        if key in self.action_weights:
            return self.action_weights[key]
        if key.startswith("phase_"):
            phase_name = key.replace("phase_", "")
            if phase_name in self.phase_params:
                return self.phase_params[phase_name].__dict__.get(key.split("_")[-1], default)
        return getattr(self, key, default)
    
    def to_dict(self) -> dict:
        return {
            "genome_id": self.genome_id,
            "generation": self.generation,
            "action_weights": self.action_weights,
            "synergy_map": {f"{a}|{b}": v for (a, b), v in self.synergy_map.items()},
            "phase_params": {k: v.__dict__ for k, v in self.phase_params.items()},
            "resource_conservation": self.resource_conservation,
            "time_optimization": self.time_optimization,
            "domain": self.domain,
            "fitness_score": self.fitness_score,
        }


class EvolutionaryCOAGenerator:
    """
    Evolves tactical DNA to generate optimized COAs.
    
    Uses evolutionary algorithms to improve COA generation over time.
    """
    
    PHASE_NAMES = ["find", "fix", "track", "target", "engage", "assess"]
    PRIMITIVE_ACTIONS = ["locate", "track", "engage", "assess", "jam", "strike", 
                         "hack", "decoy", "pinpoint", "suppress"]
    
    def __init__(self, evolution_lab: Optional[Any] = None):
        # Optional integration with EvolutionLab
        self.evolution_lab = evolution_lab
        self.population: List[EvolutionaryGenome] = []
        self.active_genome: Optional[EvolutionaryGenome] = None
        self._initialized = False
    
    def initialize_default_genome(self, agent_id: str = "evolutionary-agent") -> EvolutionaryGenome:
        """Create a default tactical genome."""
        genome = EvolutionaryGenome(
            genome_id=f"GEN-{random.randint(10000, 99999)}",
            agent_id=agent_id,
            action_weights={action: random.uniform(0.5, 1.0) 
                          for action in self.PRIMITIVE_ACTIONS},
            synergy_map=self._generate_random_synergies(),
            phase_params={phase: PhaseParameters() for phase in self.PHASE_NAMES},
            resource_conservation=random.uniform(0.6, 0.9),
            time_optimization=random.uniform(0.8, 1.2),
            mutation_rate=0.15,
        )
        self.active_genome = genome
        self.population = [genome]
        self._initialized = True
        return genome
    
    def _generate_random_synergies(self) -> Dict[tuple, float]:
        """Generate random action synergies."""
        synergies = {}
        for i, a1 in enumerate(self.PRIMITIVE_ACTIONS):
            for a2 in self.PRIMITIVE_ACTIONS[i+1:]:
                synergies[(a1, a2)] = random.uniform(0.0, 1.0)
        return synergies
    
    def mutate_genome(self, genome: EvolutionaryGenome) -> EvolutionaryGenome:
        """Create a mutated copy of genome with domain safety."""
        child = EvolutionaryGenome(
            genome_id=f"GEN-{random.randint(10000, 99999)}",
            generation=genome.generation + 1,
            agent_id=genome.agent_id,
            action_weights=genome.action_weights.copy(),
            synergy_map=genome.synergy_map.copy(),
            phase_params={k: PhaseParameters(**v.__dict__) 
                        for k, v in genome.phase_params.items()},
            resource_conservation=genome.resource_conservation,
            time_optimization=genome.time_optimization,
            domain=genome.domain,
            mutation_rate=genome.mutation_rate,
        )
        
        # Mutate action weights (Gaussian)
        for action in child.action_weights:
            if random.random() < genome.mutation_rate:
                sigma = 0.2
                child.action_weights[action] = max(0.0, min(1.0,
                    child.action_weights[action] + random.gauss(0, sigma)))
        
        # Mutate synergies (small changes)
        for (a1, a2) in list(child.synergy_map.keys()):
            if random.random() < genome.mutation_rate:
                child.synergy_map[(a1, a2)] = max(0.0, min(1.0,
                    child.synergy_map[(a1, a2)] + random.gauss(0, 0.1)))
        
        # Mutate phase parameters
        for phase in child.phase_params:
            if random.random() < genome.mutation_rate:
                child.phase_params[phase].speed = max(0.1, min(2.0,
                    child.phase_params[phase].speed + random.gauss(0, 0.2)))
                child.phase_params[phase].confidence_threshold = max(0.3, min(0.99,
                    child.phase_params[phase].confidence_threshold + random.gauss(0, 0.1)))
        
        # Mutate efficiency parameters
        if random.random() < genome.mutation_rate:
            child.resource_conservation = max(0.3, min(1.0,
                child.resource_conservation + random.gauss(0, 0.1)))
            child.time_optimization = max(0.5, min(2.0,
                child.time_optimization + random.gauss(0, 0.2)))
        
        # Ensure ROE compliance
        if violates_roe(child, genome.domain):
            # Revert to parent values
            child.action_weights = genome.action_weights.copy()
            child.synergy_map = genome.synergy_map.copy()
        
        return child
    
    def crossover_genomes(self, parent_a: EvolutionaryGenome, 
                         parent_b: EvolutionaryGenome) -> EvolutionaryGenome:
        """Safe crossover preserving domain compatibility."""
        child = EvolutionaryGenome(
            genome_id=f"GEN-{random.randint(10000, 99999)}",
            generation=max(parent_a.generation, parent_b.generation) + 1,
            agent_id=parent_a.agent_id,
            domain=parent_a.domain,
            mutation_rate=random.uniform(0.1, 0.2),
        )
        
        # Uniform crossover for action weights
        for action in self.PRIMITIVE_ACTIONS:
            if action in parent_a.action_weights and action in parent_b.action_weights:
                alpha = random.uniform(0.3, 0.7)
                child.action_weights[action] = (
                    alpha * parent_a.action_weights[action] +
                    (1 - alpha) * parent_b.action_weights[action]
                )
        
        # Blend synergies
        all_edges = set(parent_a.synergy_map.keys()) | set(parent_b.synergy_map.keys())
        for edge in all_edges:
            if edge in parent_a.synergy_map and edge in parent_b.synergy_map:
                alpha = random.uniform(0.4, 0.6)
                child.synergy_map[edge] = (
                    alpha * parent_a.synergy_map[edge] +
                    (1 - alpha) * parent_b.synergy_map[edge]
                )
        
        # Average phase parameters
        for phase in self.PHASE_NAMES:
            pa = parent_a.phase_params.get(phase, PhaseParameters())
            pb = parent_b.phase_params.get(phase, PhaseParameters())
            alpha = random.uniform(0.4, 0.6)
            child.phase_params[phase] = PhaseParameters(
                speed=alpha * pa.speed + (1 - alpha) * pb.speed,
                confidence_threshold=alpha * pa.confidence_threshold + (1 - alpha) * pb.confidence_threshold,
            )
        
        # Average efficiency parameters
        child.resource_conservation = (parent_a.resource_conservation + parent_b.resource_conservation) / 2
        child.time_optimization = (parent_a.time_optimization + parent_b.time_optimization) / 2
        
        return child
    
    def generate_evolved_coa(self, target_info: Dict[str, Any], 
                            context: Optional[Dict[str, Any]] = None) -> Any:
        """Generate a COA using evolved tactical DNA."""
        from .course_of_action import CourseOfAction
        
        if not self._initialized:
            self.initialize_default_genome()
        
        domain = target_info.get("domain", "all")
        target_type = target_info.get("type", "unknown")
        
        # Select actions based on evolved weights
        available_actions = [a for a in self.PRIMITIVE_ACTIONS 
                           if self.active_genome.action_weights.get(a, 0) > 0.5]
        
        # Build action sequence
        phases = ["locate"]
        
        # Add weighted actions
        for action in available_actions:
            if random.random() < self.active_genome.action_weights.get(action, 0.5):
                phases.append(action)
        
        phases.append("engage")
        phases.append("assess")
        
        coa = CourseOfAction(
            coa_id=f"COA-EVO-{random.randint(1000, 9999)}",
            name="Evolved Tactical Plan",
            description=f"Evolutionarily optimized COA for {domain}/{target_type}",
            domain=domain,
            phases=phases,
            required_assets=available_actions[:3],
            estimated_time_ms=random.uniform(20000, 80000),
            risk_level=random.uniform(0.3, 0.7),
            novelty_score=self._calculate_novelty(available_actions),
        )
        
        return coa
    
    def _calculate_novelty(self, actions: List[str]) -> float:
        """Calculate novelty based on action combination complexity."""
        unique_actions = len(set(actions))
        return min(1.0, unique_actions / len(self.PRIMITIVE_ACTIONS))
    
    def evaluate_fitness(self, genome: EvolutionaryGenome, 
                        telemetry_data: Dict[str, Any]) -> float:
        """Calculate fitness for a genome based on performance data."""
        # Effectiveness: hits/attempts
        hits = telemetry_data.get("hits", 0)
        attempts = telemetry_data.get("attempts", 1)
        effectiveness = hits / max(1, attempts)
        
        # Efficiency: resource usage
        weapons_used = telemetry_data.get("weapons_used", 1)
        weapons_allocated = telemetry_data.get("weapons_allocated", 1)
        efficiency = 1.0 - (weapons_used / max(1, weapons_allocated))
        
        # Novelty: complex action combinations
        actions_used = telemetry_data.get("actions_used", [])
        novelty = self._calculate_novelty(actions_used)
        
        # Combined score
        fitness = 0.5 * effectiveness + 0.3 * efficiency + 0.2 * novelty
        
        # Apply penalties
        if telemetry_data.get("blue_on_blue", 0) > 0:
            fitness *= 0.01
        elif telemetry_data.get("collateral", 0) > 0:
            fitness *= 0.7
        
        genome.fitness_score = fitness
        genome.fitness_history.append(fitness)
        return fitness
    
    def evolve_generation(self) -> Optional[EvolutionaryGenome]:
        """Run one generation of evolution."""
        if len(self.population) < 2:
            return None
        
        # Sort by fitness
        self.population.sort(key=lambda g: g.fitness_score, reverse=True)
        
        # Keep best (elitism)
        survivors = self.population[:max(1, len(self.population) // 2)]
        
        # Generate offspring
        offspring = []
        while len(survivors) + len(offspring) < len(self.population):
            parent_a = random.choice(survivors)
            parent_b = random.choice(survivors)
            
            if random.random() < 0.7:
                child = self.crossover_genomes(parent_a, parent_b)
            else:
                child = self.mutate_genome(parent_a)
            
            offspring.append(child)
        
        self.population = survivors + offspring
        self.active_genome = self.population[0]
        return self.active_genome
    
    def get_stats(self) -> dict:
        return {
            "population_size": len(self.population),
            "active_fitness": self.active_genome.fitness_score if self.active_genome else 0,
            "generations_run": self.active_genome.generation if self.active_genome else 0,
        }