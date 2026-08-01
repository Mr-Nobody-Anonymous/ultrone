# Copyright (c) Ultrone Contributors. All rights reserved.
"""Evolutionary COA Generator - evolves tactical DNA using GEP."""

from __future__ import annotations

import random
import logging
import math
from typing import Any, Dict, List, Optional, TYPE_CHECKING
from dataclasses import dataclass, field
from enum import Enum

if TYPE_CHECKING:
    from brain.learning.evolution_lab import EvolutionLab
    from sim import WorldState
    from data.entities import Unit
    from .swarm_genomes import CommanderGenome, AssetMicroGenome

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
    
    Phase 1 Swarm Support:
    - Population can contain CommanderGenome instances.
    - When evaluating a CommanderGenome, it spawns AssetMicroGenomes.
    - Swarm collision penalty is applied in fitness evaluation.
    """
    
    PHASE_NAMES = ["find", "fix", "track", "target", "engage", "assess"]
    PRIMITIVE_ACTIONS = ["locate", "track", "engage", "assess", "jam", "strike", 
                         "hack", "decoy", "pinpoint", "suppress"]
    
    def __init__(self, evolution_lab: Optional[Any] = None):
        # Optional integration with EvolutionLab
        self.evolution_lab = evolution_lab
        self.population: List[Any] = []  # Can contain EvolutionaryGenome or CommanderGenome
        self.active_genome: Optional[Any] = None
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
        
        # Swarm mode: CommanderGenome spawns fleet and returns hierarchical COA
        if hasattr(self.active_genome, 'spawn_asset_micro_genomes'):
            fleet = self.active_genome.spawn_asset_micro_genomes()
            coa = CourseOfAction(
                coa_id=f"COA-SWARM-{random.randint(1000, 9999)}",
                name="Swarm Tactical Plan",
                description=f"Hierarchical COA for {domain}/{target_type}",
                domain=domain,
                phases=["locate", "engage", "assess"],
                required_assets=["swarm"],
                estimated_time_ms=random.uniform(20000, 80000),
                risk_level=random.uniform(0.3, 0.7),
                novelty_score=self._calculate_novelty(["swarm"]),
            )
            coa.swarm_fleet = fleet
            coa.commander_genome = self.active_genome
            return coa
        
        # Legacy single-genome mode
        available_actions = [a for a in self.PRIMITIVE_ACTIONS 
                           if self.active_genome.action_weights.get(a, 0) > 0.5]
        
        phases = ["locate"]
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

    def evaluate_commander_fitness(self, commander: "CommanderGenome",
                                   telemetry_data: Dict[str, Any],
                                   collision_count: int = 0) -> float:
        """
        Evaluate fitness for a CommanderGenome with swarm-specific penalties.
        
        Args:
            commander: The commander genome to evaluate
            telemetry_data: Standard telemetry data
            collision_count: Number of friendly asset collisions (same-grid stacking)
        """
        # Base fitness from inherited logic
        base_fitness = self.evaluate_fitness(commander, telemetry_data)
        
        # Swarm collision penalty: heavy penalty for stacking assets in same grid square
        if collision_count > 0:
            collision_penalty = 0.5 * collision_count
            base_fitness *= max(0.0, 1.0 - collision_penalty)
        
        commander.fitness_score = base_fitness
        commander.fitness_history.append(base_fitness)
        return base_fitness
    
    def evolve_commander_generation(self, population: Optional[List["CommanderGenome"]] = None) -> Optional["CommanderGenome"]:
        """
        Run one generation of evolution for CommanderGenome swarm population.
        
        If no population provided, uses self.population.
        """
        if population is None:
            population = [g for g in self.population if hasattr(g, 'spawn_asset_micro_genomes')]
        
        if len(population) < 2:
            return None
        
        # Sort by fitness
        population.sort(key=lambda g: g.fitness_score, reverse=True)
        
        # Keep best (elitism)
        survivors = population[:max(1, len(population) // 2)]
        
        # Generate offspring
        offspring: List["CommanderGenome"] = []
        while len(survivors) + len(offspring) < len(population):
            parent_a = random.choice(survivors)
            parent_b = random.choice(survivors)
            
            if random.random() < 0.7:
                child = self._crossover_commanders(parent_a, parent_b)
            else:
                child = self._mutate_commander(parent_a)
            
            offspring.append(child)
        
        new_population = survivors + offspring
        self.population = new_population
        self.active_genome = new_population[0]
        return self.active_genome
    
    def _mutate_commander(self, commander: "CommanderGenome") -> "CommanderGenome":
        """Mutate a CommanderGenome's strategy weights and allocation."""
        from .swarm_genomes import CommanderGenome
        child = CommanderGenome(
            genome_id=f"GEN-{random.randint(10000, 99999)}",
            generation=commander.generation + 1,
            agent_id=commander.agent_id,
            action_weights=commander.action_weights.copy(),
            synergy_map=commander.synergy_map.copy(),
            phase_params={k: PhaseParameters(**v.__dict__) for k, v in commander.phase_params.items()},
            resource_conservation=commander.resource_conservation,
            time_optimization=commander.time_optimization,
            domain=commander.domain,
            mutation_rate=commander.mutation_rate,
            allocation_weights=commander.allocation_weights.copy(),
        )
        
        # Mutate allocation weights
        for key in child.allocation_weights:
            if random.random() < commander.mutation_rate:
                child.allocation_weights[key] = max(0.0, min(1.0,
                    child.allocation_weights[key] + random.gauss(0, 0.1)))
        
        # Mutate base tactical parameters too
        for action in child.action_weights:
            if random.random() < commander.mutation_rate:
                sigma = 0.2
                child.action_weights[action] = max(0.0, min(1.0,
                    child.action_weights[action] + random.gauss(0, sigma)))
        
        return child
    
    def _crossover_commanders(self, parent_a: "CommanderGenome", 
                              parent_b: "CommanderGenome") -> "CommanderGenome":
        """Crossover two CommanderGenomes, blending strategy and allocations."""
        from .swarm_genomes import CommanderGenome
        child = CommanderGenome(
            genome_id=f"GEN-{random.randint(10000, 99999)}",
            generation=max(parent_a.generation, parent_b.generation) + 1,
            agent_id=parent_a.agent_id,
            domain=parent_a.domain,
            mutation_rate=random.uniform(0.1, 0.2),
            action_weights={},
            synergy_map={},
            phase_params={},
        )
        
        # Blend action weights
        all_actions = set(parent_a.action_weights.keys()) | set(parent_b.action_weights.keys())
        for action in all_actions:
            a = parent_a.action_weights.get(action, 0.5)
            b = parent_b.action_weights.get(action, 0.5)
            alpha = random.uniform(0.4, 0.6)
            child.action_weights[action] = max(0.0, min(1.0, alpha * a + (1 - alpha) * b))
        
        # Blend allocation weights
        all_keys = set(parent_a.allocation_weights.keys()) | set(parent_b.allocation_weights.keys())
        for key in all_keys:
            a = parent_a.allocation_weights.get(key, 0.0)
            b = parent_b.allocation_weights.get(key, 0.0)
            alpha = random.uniform(0.4, 0.6)
            child.allocation_weights[key] = max(0.0, min(1.0, alpha * a + (1 - alpha) * b))
        
        # Copy phase_params from parent_a if missing
        if not child.phase_params and parent_a.phase_params:
            child.phase_params = {k: PhaseParameters(**v.__dict__) for k, v in parent_a.phase_params.items()}
        
        return child
    
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


# ═══════════════════════════════════════════════════════════════════
#  Generative & Evolutionary Enhancements
# ═══════════════════════════════════════════════════════════════════

# ── 1. Generative Adversarial Coevolution (GAN-style) ────────────

class GenerativeAdversarialCoevolution:
    """
    GAN-style adversarial coevolution between Blue and Red populations.
    
    Blue (Generator) tries to create tactics that defeat the current Red.
    Red (Discriminator) tries to evolve defenses against Blue's best tactics.
    This creates an endless adversarial arms race, like GANs.
    
    Features:
    - Generator/Discriminator fitness alternation
    - Adversarial pressure balancing
    - Mode collapse detection (when one side dominates)
    - Gradient-based fitness shaping
    """

    def __init__(self, coevolution_engine: Any = None,
                 gen_weight: float = 0.6, disc_weight: float = 0.4):
        self.coevolution = coevolution_engine
        self.gen_weight = gen_weight  # Blue generator weight
        self.disc_weight = disc_weight  # Red discriminator weight
        self.generation: int = 0
        self.blue_wins: int = 0
        self.red_wins: int = 0
        self.mode_collapse_count: int = 0
        self._adversarial_history: List[Dict[str, float]] = []

    def compute_adversarial_fitness(self, blue_fitness: float, red_fitness: float) -> tuple:
        """
        Compute GAN-style adversarial fitness.
        
        Blue fitness is boosted when Red fitness is low (Blue is "fooling" Red).
        Red fitness is boosted when it successfully counters Blue.
        
        Returns:
            (adjusted_blue_fitness, adjusted_red_fitness)
        """
        # Generator (Blue) wants to maximize: log(D(Blue_success)) 
        # Discriminator (Red) wants to maximize: log(1 - D(Blue_success))
        
        # Map to [0, 1] range
        blue_success = min(1.0, max(0.0, blue_fitness))
        red_success = min(1.0, max(0.0, red_fitness))
        
        # Adversarial objective: Blue wants Red to fail
        adversarial_blue = blue_fitness * (1.0 - red_success) * self.gen_weight
        adversarial_red = red_fitness * (1.0 - blue_success) * self.disc_weight
        
        # Track mode collapse (when one side dominates excessively)
        if blue_fitness > 0.8 and red_fitness < 0.2:
            self.mode_collapse_count += 1
        elif red_fitness > 0.8 and blue_fitness < 0.2:
            self.mode_collapse_count += 1
        else:
            self.mode_collapse_count = max(0, self.mode_collapse_count - 1)
        
        if blue_fitness > red_fitness:
            self.blue_wins += 1
        else:
            self.red_wins += 1
        
        self.generation += 1
        self._adversarial_history.append({
            "generation": self.generation,
            "blue_fitness": blue_fitness,
            "red_fitness": red_fitness,
            "adversarial_blue": adversarial_blue,
            "adversarial_red": adversarial_red,
            "mode_collapse": self.mode_collapse_count,
        })
        
        return adversarial_blue, adversarial_red

    def is_stable(self, window: int = 10) -> bool:
        """Check if adversarial coevolution is stable (no mode collapse)."""
        if len(self._adversarial_history) < window:
            return True
        recent = self._adversarial_history[-window:]
        blue_avg = sum(r["blue_fitness"] for r in recent) / window
        red_avg = sum(r["red_fitness"] for r in recent) / window
        diff = abs(blue_avg - red_avg)
        return diff < 0.3  # Both sides within 0.3 of each other

    def get_stats(self) -> dict:
        return {
            "generation": self.generation,
            "blue_wins": self.blue_wins,
            "red_wins": self.red_wins,
            "mode_collapse_count": self.mode_collapse_count,
            "stable": self.is_stable(),
            "total_rounds": self.blue_wins + self.red_wins,
        }


# ── 2. Neural Topology Evolution (NEAT-inspired) ─────────────────

@dataclass
class NeuralNodeGene:
    """A node in a neural network topology."""
    node_id: int
    node_type: str = "hidden"  # input, hidden, output
    activation: str = "relu"  # relu, tanh, sigmoid, linear
    bias: float = 0.0


@dataclass
class NeuralConnectionGene:
    """A connection between two nodes in a neural topology."""
    innov_id: int
    from_node: int
    to_node: int
    weight: float = 0.0
    enabled: bool = True


class NeuralTopologyEvolution:
    """
    NEAT-inspired neural network topology evolution.
    
    Evolves both weights and network structure (adding nodes/connections).
    Uses innovation numbers for crossover compatibility.
    
    Features:
    - Add node mutation (split connection)
    - Add connection mutation
    - Weight mutation (gaussian, uniform)
    - Structural crossover with innovation matching
    - Speciation to protect innovation
    """

    def __init__(self, n_inputs: int = 10, n_outputs: int = 5,
                 pop_size: int = 20, mutation_rate: float = 0.3):
        self.n_inputs = n_inputs
        self.n_outputs = n_outputs
        self.pop_size = pop_size
        self.mutation_rate = mutation_rate
        self.global_innovation: int = 0
        self.population: List[Dict[str, Any]] = []
        self.species: Dict[int, List[int]] = {}  # species_id -> [individual_indices]
        self._next_species_id: int = 0

    def _create_initial_topology(self) -> Dict[str, Any]:
        """Create a minimal topology with all inputs connected to all outputs."""
        nodes = {}
        connections = {}
        
        # Input nodes
        for i in range(self.n_inputs):
            node = NeuralNodeGene(node_id=i, node_type="input", activation="linear")
            nodes[i] = node
        
        # Output nodes
        offset = self.n_inputs
        for i in range(self.n_outputs):
            node = NeuralNodeGene(node_id=offset + i, node_type="output", activation="sigmoid")
            nodes[offset + i] = node
        
        # Fully connect inputs to outputs
        innov = 0
        for i in range(self.n_inputs):
            for j in range(self.n_outputs):
                conn = NeuralConnectionGene(
                    innov_id=innov,
                    from_node=i,
                    to_node=offset + j,
                    weight=random.uniform(-1.0, 1.0),
                    enabled=True,
                )
                connections[innov] = conn
                innov += 1
        
        self.global_innovation = max(self.global_innovation, innov)
        
        return {
            "nodes": nodes,
            "connections": connections,
            "fitness": 0.0,
            "species_id": None,
        }

    def initialize_population(self) -> None:
        """Create initial population of topologies."""
        self.population = []
        for _ in range(self.pop_size):
            individual = self._create_initial_topology()
            individual["species_id"] = self._speciate(individual)
            self.population.append(individual)

    def _speciate(self, individual: Dict[str, Any]) -> int:
        """Assign individual to a species based on topological similarity."""
        if not self.species:
            species_id = self._next_species_id
            self._next_species_id += 1
            self.species[species_id] = []
            return species_id
        
        # Compare with representative of each species
        best_species = None
        best_compatibility = float("inf")
        
        for species_id, members in self.species.items():
            if not members:
                continue
            rep_idx = members[0]
            if rep_idx < len(self.population):
                rep = self.population[rep_idx]
                compatibility = self._compute_compatibility(individual, rep)
                if compatibility < best_compatibility:
                    best_compatibility = compatibility
                    best_species = species_id
        
        if best_species is not None and best_compatibility < 1.0:
            return best_species
        
        # Create new species
        species_id = self._next_species_id
        self._next_species_id += 1
        self.species[species_id] = []
        return species_id

    def _compute_compatibility(self, ind1: Dict[str, Any], ind2: Dict[str, Any]) -> float:
        """Compute topological compatibility between two individuals."""
        conn1 = set(ind1["connections"].keys())
        conn2 = set(ind2["connections"].keys())
        
        n_disjoint = len(conn1.symmetric_difference(conn2))
        n_excess = max(0, len(conn1) - len(conn2)) if len(conn1) > len(conn2) else max(0, len(conn2) - len(conn1))
        
        # Average weight difference of matching connections
        matching = conn1 & conn2
        if matching:
            weight_diff = sum(
                abs(ind1["connections"][c].weight - ind2["connections"][c].weight)
                for c in matching
            ) / len(matching)
        else:
            weight_diff = 0.0
        
        return n_disjoint * 1.0 + n_excess * 0.5 + weight_diff * 0.4

    def mutate_topology(self, individual: Dict[str, Any]) -> None:
        """Mutate the neural topology (structure + weights)."""
        if random.random() < self.mutation_rate * 0.5:
            self._mutate_add_node(individual)
        if random.random() < self.mutation_rate * 0.3:
            self._mutate_add_connection(individual)
        if random.random() < self.mutation_rate * 0.8:
            self._mutate_weights(individual)

    def _mutate_add_node(self, individual: Dict[str, Any]) -> None:
        """Add a node by splitting a random connection."""
        connections = individual["connections"]
        if not connections:
            return
        
        # Pick a random connection to split
        conn_id = random.choice(list(connections.keys()))
        conn = connections[conn_id]
        conn.enabled = False  # Disable old connection
        
        # Create new node
        new_node_id = max(individual["nodes"].keys()) + 1
        new_node = NeuralNodeGene(
            node_id=new_node_id,
            node_type="hidden",
            activation=random.choice(["relu", "tanh", "sigmoid"]),
        )
        individual["nodes"][new_node_id] = new_node
        
        # Create connection from old from_node to new node
        self.global_innovation += 1
        conn1 = NeuralConnectionGene(
            innov_id=self.global_innovation,
            from_node=conn.from_node, to_node=new_node_id,
            weight=1.0, enabled=True,
        )
        individual["connections"][self.global_innovation] = conn1
        
        # Create connection from new node to old to_node
        self.global_innovation += 1
        conn2 = NeuralConnectionGene(
            innov_id=self.global_innovation,
            from_node=new_node_id, to_node=conn.to_node,
            weight=conn.weight, enabled=True,
        )
        individual["connections"][self.global_innovation] = conn2

    def _mutate_add_connection(self, individual: Dict[str, Any]) -> None:
        """Add a new connection between two unconnected nodes."""
        nodes = list(individual["nodes"].keys())
        existing = {(c.from_node, c.to_node) for c in individual["connections"].values()}
        
        # Find unconnected pairs
        candidates = []
        for from_node in nodes:
            for to_node in nodes:
                if from_node != to_node and (from_node, to_node) not in existing:
                    candidates.append((from_node, to_node))
        
        if candidates:
            from_node, to_node = random.choice(candidates)
            self.global_innovation += 1
            conn = NeuralConnectionGene(
                innov_id=self.global_innovation,
                from_node=from_node, to_node=to_node,
                weight=random.uniform(-1.0, 1.0),
                enabled=True,
            )
            individual["connections"][self.global_innovation] = conn

    def _mutate_weights(self, individual: Dict[str, Any]) -> None:
        """Mutate connection weights."""
        for conn in individual["connections"].values():
            if random.random() < self.mutation_rate:
                if random.random() < 0.9:
                    # Gaussian perturbation
                    conn.weight += random.gauss(0, 0.1)
                else:
                    # Reset
                    conn.weight = random.uniform(-1.0, 1.0)
                conn.weight = max(-3.0, min(3.0, conn.weight))

    def crossover(self, parent1: Dict[str, Any], parent2: Dict[str, Any]) -> Dict[str, Any]:
        """Crossover two topologies (matching connections by innovation number)."""
        child = {
            "nodes": {},
            "connections": {},
            "fitness": 0.0,
            "species_id": None,
        }
        
        # Inherit nodes (union of both parents)
        all_node_ids = set(parent1["nodes"].keys()) | set(parent2["nodes"].keys())
        for nid in all_node_ids:
            if nid in parent1["nodes"]:
                child["nodes"][nid] = parent1["nodes"][nid]
            else:
                child["nodes"][nid] = parent2["nodes"][nid]
        
        # Crossover connections by innovation number
        conn1 = parent1["connections"]
        conn2 = parent2["connections"]
        all_innovs = set(conn1.keys()) | set(conn2.keys())
        
        for innov in all_innovs:
            if innov in conn1 and innov in conn2:
                # Matching: randomly choose one
                child["connections"][innov] = random.choice([conn1[innov], conn2[innov]])
            elif innov in conn1:
                # Disjoint/excess: inherit from fitter parent
                if parent1.get("fitness", 0.0) >= parent2.get("fitness", 0.0):
                    child["connections"][innov] = conn1[innov]
            else:
                if parent2.get("fitness", 0.0) > parent1.get("fitness", 0.0):
                    child["connections"][innov] = conn2[innov]
        
        return child

    def evolve_generation(self, fitness_scores: List[float]) -> None:
        """
        Evolve one generation using fitness scores.
        
        Args:
            fitness_scores: List of fitness values matching self.population order
        """
        if len(fitness_scores) != len(self.population):
            return
        
        # Update fitness
        for i, f in enumerate(fitness_scores):
            self.population[i]["fitness"] = f
        
        # Sort by fitness
        sorted_indices = sorted(range(len(self.population)),
                               key=lambda i: self.population[i]["fitness"],
                               reverse=True)
        
        # Keep top half (elitism)
        survivors = [self.population[i] for i in sorted_indices[:len(self.population)//2]]
        
        # Generate offspring
        offspring = []
        while len(survivors) + len(offspring) < len(self.population):
            p1 = random.choice(survivors)
            p2 = random.choice(survivors)
            if random.random() < 0.7:
                child = self.crossover(p1, p2)
            else:
                child = self._create_initial_topology()
            self.mutate_topology(child)
            child["species_id"] = self._speciate(child)
            offspring.append(child)
        
        self.population = survivors + offspring

    def get_stats(self) -> dict:
        return {
            "population_size": len(self.population),
            "num_species": len(self.species),
            "global_innovation": self.global_innovation,
            "avg_nodes": sum(len(ind["nodes"]) for ind in self.population) / max(1, len(self.population)),
            "avg_connections": sum(len(ind["connections"]) for ind in self.population) / max(1, len(self.population)),
        }


# ── 3. Evolutionary Strategy Optimizer (NES) ─────────────────────

class EvolutionaryStrategyOptimizer:
    """
    Natural Evolution Strategies (NES) for parameter optimization.
    
    Uses a population-based gradient estimate to optimize continuous parameters.
    More efficient than standard genetic algorithms for real-valued optimization.
    
    Features:
    - Fitness shaping (ranking)
    - Antithetic sampling (symmetry)
    - Utils for covariance adaptation
    - Separable NES (SNES) for high-dimensional problems
    """

    def __init__(self, param_dims: int = 10, pop_size: int = 20,
                 learning_rate: float = 0.01, sigma: float = 0.1):
        self.param_dims = param_dims
        self.pop_size = pop_size
        self.learning_rate = learning_rate
        self.sigma = sigma  # Mutation strength
        self.mean = [0.0] * param_dims
        self.cov = [[1.0 if i == j else 0.0 for j in range(param_dims)] for i in range(param_dims)]
        self._fitness_history: List[float] = []

    def _try_import_numpy(self):
        """Try to import numpy, fall back to basic math."""
        try:
            import numpy as np
            return np
        except ImportError:
            return None

    def sample_population(self) -> List[List[float]]:
        """Sample a population of parameters from the current distribution."""
        np = self._try_import_numpy()
        if np is not None:
            samples = np.random.multivariate_normal(self.mean, self.cov * self.sigma**2, self.pop_size)
            return [list(s) for s in samples]
        else:
            # Fallback: simple gaussian sampling per dimension
            samples = []
            for _ in range(self.pop_size):
                sample = []
                for d in range(self.param_dims):
                    sample.append(random.gauss(self.mean[d], self.sigma))
                samples.append(sample)
            return samples

    def update_distribution(self, samples: List[List[float]], 
                           fitness_scores: List[float]) -> None:
        """
        Update the search distribution using rank-based fitness shaping.
        
        Args:
            samples: List of sampled parameter vectors
            fitness_scores: Corresponding fitness values (higher is better)
        """
        np = self._try_import_numpy()
        
        # Rank-based fitness shaping (utility)
        log = math.log if np is None else np.log
        n = len(fitness_scores)
        ranks = sorted(range(n), key=lambda i: fitness_scores[i], reverse=True)
        utilities = [max(0.0, log(n/2 + 1) - log(rank + 1)) for rank in ranks]
        # Normalize
        sum_u = sum(utilities)
        if sum_u > 0:
            utilities = [u / sum_u - 1.0/n for u in utilities]
        else:
            utilities = [0.0] * n
        
        if np is not None:
            samples_np = np.array(samples)
            # Compute gradient
            grad = np.zeros(self.param_dims)
            for i in range(n):
                grad += utilities[i] * (samples_np[i] - self.mean) / self.sigma
            
            # Update mean
            self.mean = self.mean + self.learning_rate * grad
            
            # Update covariance (simplified)
            grad_cov = np.zeros((self.param_dims, self.param_dims))
            for i in range(n):
                z = (samples_np[i] - self.mean) / self.sigma
                grad_cov += utilities[i] * (np.outer(z, z) - np.eye(self.param_dims))
            
            self.cov = self.cov + self.learning_rate * grad_cov * 0.1
            # Ensure positive semi-definite
            eigvals, eigvecs = np.linalg.eigh(self.cov)
            eigvals = np.maximum(eigvals, 1e-6)
            self.cov = eigvecs @ np.diag(eigvals) @ eigvecs.T
        else:
            # Simplified update without numpy
            for d in range(self.param_dims):
                grad = 0.0
                for i in range(n):
                    grad += utilities[i] * (samples[i][d] - self.mean[d]) / self.sigma
                self.mean[d] += self.learning_rate * grad
        
        best_fitness = max(fitness_scores) if fitness_scores else 0.0
        self._fitness_history.append(best_fitness)

    def get_stats(self) -> dict:
        return {
            "param_dims": self.param_dims,
            "pop_size": self.pop_size,
            "sigma": self.sigma,
            "learning_rate": self.learning_rate,
            "best_fitness": max(self._fitness_history) if self._fitness_history else 0.0,
            "generations": len(self._fitness_history),
        }


# ── 4. Generative Tactical Variant Engine ─────────────────────────

class GenerativeTacticalVariantEngine:
    """
    Generative AI engine for creating novel tactical variants.
    
    Uses evolutionary algorithms to generate and combine tactical
    patterns into novel COAs. Supports:
    - Tactical pattern extraction from successful COAs
    - Pattern recombination (crossover at tactical level)
    - Novelty-based generation for exploration
    - Constraint-aware generation (ROE, domain limits)
    """

    def __init__(self):
        self.tactical_patterns: Dict[str, Dict[str, Any]] = {}
        self._pattern_library: List[Dict[str, Any]] = []
        self._generation_count: int = 0

    def extract_pattern(self, coa: Any) -> Dict[str, Any]:
        """Extract a tactical pattern from a successful COA."""
        if hasattr(coa, 'phases'):
            phases = coa.phases
        elif isinstance(coa, dict):
            phases = coa.get("phases", [])
        else:
            phases = []
        
        pattern = {
            "pattern_id": f"PTN-{random.randint(10000, 99999)}",
            "phases": phases,
            "action_sequence": phases,
            "novelty": getattr(coa, 'novelty_score', 0.0) if hasattr(coa, 'novelty_score') else 0.0,
            "success_rate": 1.0,
            "generation": self._generation_count,
        }
        
        pattern_key = "-".join(phases) if phases else f"pattern-{len(self._pattern_library)}"
        self.tactical_patterns[pattern_key] = pattern
        self._pattern_library.append(pattern)
        return pattern

    def recombine_patterns(self, pattern_a: Dict[str, Any],
                          pattern_b: Dict[str, Any]) -> Dict[str, Any]:
        """Recombine two tactical patterns to create a novel variant."""
        phases_a = pattern_a.get("phases", [])
        phases_b = pattern_b.get("phases", [])
        
        if not phases_a or not phases_b:
            return pattern_a if phases_a else pattern_b
        
        # Single-point crossover
        crossover_point = random.randint(1, min(len(phases_a), len(phases_b)) - 1)
        new_phases = phases_a[:crossover_point] + phases_b[crossover_point:]
        
        # Remove duplicates while preserving order
        seen = set()
        unique_phases = []
        for p in new_phases:
            if p not in seen:
                seen.add(p)
                unique_phases.append(p)
        
        novelty = (pattern_a.get("novelty", 0.0) + pattern_b.get("novelty", 0.0)) / 2
        # Add novelty boost for recombination
        novelty = min(1.0, novelty * 1.2 + 0.1)
        
        pattern = {
            "pattern_id": f"PTN-RECOMB-{random.randint(10000, 99999)}",
            "phases": unique_phases,
            "action_sequence": unique_phases,
            "novelty": novelty,
            "success_rate": 0.5,  # Unknown, start at 50%
            "generation": self._generation_count,
            "parents": [pattern_a.get("pattern_id"), pattern_b.get("pattern_id")],
        }
        
        self._pattern_library.append(pattern)
        self._generation_count += 1
        return pattern

    def generate_novel_variant(self, base_pattern: Dict[str, Any],
                              constraints: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Generate a novel variant by mutating a base pattern."""
        constraints = constraints or {}
        phases = list(base_pattern.get("phases", []))
        
        if not phases:
            return base_pattern
        
        # Mutation: insert, delete, or swap phases
        mutation_type = random.choice(["insert", "delete", "swap", "shuffle"])
        
        available_actions = ["locate", "track", "engage", "assess", "jam", "strike",
                            "hack", "decoy", "pinpoint", "suppress", "recon", "scan"]
        
        # Apply domain constraints
        domain = constraints.get("domain", "all")
        if domain != "all":
            domain_actions = {
                "air": ["locate", "track", "engage", "strike", "decoy", "scan"],
                "cyber": ["jam", "hack", "silence", "recon"],
                "sea": ["locate", "track", "engage", "strike", "suppress", "pinpoint"],
                "land": ["locate", "track", "engage", "strike", "suppress"],
                "space": ["scan", "jam", "decoy", "recon"],
            }
            valid_actions = domain_actions.get(domain, available_actions)
        else:
            valid_actions = available_actions
        
        if mutation_type == "insert" and len(phases) < 15:
            pos = random.randint(0, len(phases))
            new_action = random.choice(valid_actions)
            phases.insert(pos, new_action)
        elif mutation_type == "delete" and len(phases) > 1:
            pos = random.randint(0, len(phases) - 1)
            phases.pop(pos)
        elif mutation_type == "swap" and len(phases) >= 2:
            i, j = random.sample(range(len(phases)), 2)
            phases[i], phases[j] = phases[j], phases[i]
        elif mutation_type == "shuffle":
            random.shuffle(phases)
        
        novelty = min(1.0, base_pattern.get("novelty", 0.0) * 1.1 + 0.05)
        
        pattern = {
            "pattern_id": f"PTN-NOVEL-{random.randint(10000, 99999)}",
            "phases": phases,
            "action_sequence": phases,
            "novelty": novelty,
            "success_rate": 0.3,  # Unknown novel variant, start conservative
            "generation": self._generation_count,
            "parent": base_pattern.get("pattern_id"),
            "mutation_type": mutation_type,
        }
        
        self._pattern_library.append(pattern)
        self._generation_count += 1
        return pattern

    def get_best_patterns(self, n: int = 5) -> List[Dict[str, Any]]:
        """Get top N patterns by novelty * success_rate."""
        scored = [(p, p.get("novelty", 0.0) * p.get("success_rate", 0.0))
                  for p in self._pattern_library]
        scored.sort(key=lambda x: x[1], reverse=True)
        return [p for p, _ in scored[:n]]

    def get_stats(self) -> dict:
        return {
            "total_patterns": len(self._pattern_library),
            "generations": self._generation_count,
            "unique_patterns": len(self.tactical_patterns),
            "best_novelty": max((p.get("novelty", 0.0) for p in self._pattern_library), default=0.0),
            "avg_novelty": (sum(p.get("novelty", 0.0) for p in self._pattern_library) / 
                          max(1, len(self._pattern_library))) if self._pattern_library else 0.0,
        }


# ── 5. Enhanced Mutation Operators ────────────────────────────────

class MutationStrategy(Enum):
    """Enhanced mutation strategies."""
    GAUSSIAN = "gaussian"       # Standard gaussian perturbation
    UNIFORM = "uniform"         # Random uniform resampling
    ADAPTIVE = "adaptive"       # Self-adaptive mutation rate
    SELF_ADAPTIVE = "self_adaptive"  # Each gene has its own mutation rate
    CORRELATED = "correlated"   # Correlated mutations across gene groups
    LAMARCKIAN = "lamarckian"   # Acquired traits passed to offspring
    SALTATION = "saltation"     # Large jumps (macro-mutation)
    POLYNOMIAL = "polynomial"   # Polynomial mutation (NSGA-II style)


class EnhancedMutationOperator:
    """
    Advanced mutation operators with self-adaptation, correlation, and Lamarckian learning.
    
    Features:
    - Self-adaptive mutation rates (each gene evolves its own mutation rate)
    - Correlated mutation (groups of genes mutate together)
    - Lamarckian evolution (learned improvements passed to offspring)
    - Saltation (macro-mutations for escaping local optima)
    - Polynomial mutation (NSGA-II compatible)
    """

    def __init__(self, base_rate: float = 0.15,
                 strategy: str = "adaptive",
                 correlation_strength: float = 0.3):
        self.base_rate = base_rate
        self.strategy = strategy
        self.correlation_strength = correlation_strength
        self.gene_groups: Dict[str, List[str]] = {}  # group_name -> [gene_names]

    def register_gene_group(self, group_name: str, gene_names: List[str]) -> None:
        """Register a group of correlated genes."""
        self.gene_groups[group_name] = gene_names

    def mutate_gaussian(self, value: float, min_val: float, max_val: float,
                       rate: float, sigma_scale: float = 0.1) -> float:
        """Gaussian perturbation around current value."""
        if random.random() < rate:
            sigma = (max_val - min_val) * sigma_scale
            value += random.gauss(0, sigma)
            return max(min_val, min(max_val, value))
        return value

    def mutate_uniform(self, value: float, min_val: float, max_val: float,
                      rate: float) -> float:
        """Uniform random resampling within bounds."""
        if random.random() < rate:
            return random.uniform(min_val, max_val)
        return value

    def mutate_polynomial(self, value: float, min_val: float, max_val: float,
                         rate: float, eta: float = 20.0) -> float:
        """
        Polynomial mutation (NSGA-II style).
        
        Args:
            eta: Distribution index (higher = closer to parent)
        """
        if random.random() < rate:
            r = random.random()
            delta = min(value - min_val, max_val - value) / (max_val - min_val)
            if r < 0.5:
                delta_q = (2 * r + (1 - 2 * r) * (1 - delta) ** (eta + 1)) ** (1.0 / (eta + 1)) - 1
            else:
                delta_q = 1 - (2 * (1 - r) + 2 * (r - 0.5) * (1 - delta) ** (eta + 1)) ** (1.0 / (eta + 1))
            value += delta_q * (max_val - min_val)
            return max(min_val, min(max_val, value))
        return value

    def mutate_saltation(self, value: float, min_val: float, max_val: float,
                        rate: float) -> float:
        """Large jump mutation for escaping local optima."""
        if random.random() < rate * 0.1:  # Low probability
            # Jump to random position
            return random.uniform(min_val, max_val)
        return value

    def mutate_group(self, genome: EvolutionaryGenome, group_name: str) -> bool:
        """Correlated mutation of all genes in a group."""
        if group_name not in self.gene_groups:
            return False
        
        gene_names = self.gene_groups[group_name]
        if random.random() < self.base_rate:
            # Apply same direction to all genes in group
            direction = random.choice([-1, 1])
            magnitude = random.gauss(0, self.correlation_strength)
            
            for gene_name in gene_names:
                if gene_name in genome.action_weights:
                    genome.action_weights[gene_name] = max(0.0, min(1.0,
                        genome.action_weights[gene_name] + direction * magnitude))
            
            return True
        return False

    def apply_lamarckian(self, genome: EvolutionaryGenome,
                        performance_data: Dict[str, Any]) -> EvolutionaryGenome:
        """
        Lamarckian evolution: pass acquired traits to offspring.
        
        If an action performed well, increase its weight directly.
        """
        child = genome  # In-place modification
        
        actions_used = performance_data.get("actions_used", [])
        success = performance_data.get("success", False)
        
        if success:
            # Reward successful actions
            for action in actions_used:
                if action in child.action_weights:
                    child.action_weights[action] = min(1.0,
                        child.action_weights[action] + 0.05)
        else:
            # Penalize failed actions
            for action in actions_used:
                if action in child.action_weights:
                    child.action_weights[action] = max(0.0,
                        child.action_weights[action] - 0.02)
        
        return child

    def get_stats(self) -> dict:
        return {
            "strategy": self.strategy,
            "base_rate": self.base_rate,
            "correlation_strength": self.correlation_strength,
            "gene_groups": len(self.gene_groups),
        }


# ── 6. Multi-Objective Optimization (NSGA-II style) ──────────────

@dataclass
class MultiObjectiveFitness:
    """Container for multi-objective fitness scores."""
    objectives: Dict[str, float] = field(default_factory=dict)
    rank: int = 0
    crowding_distance: float = 0.0

    def __getitem__(self, key: str) -> float:
        return self.objectives.get(key, 0.0)

    def __setitem__(self, key: str, value: float) -> None:
        self.objectives[key] = value


class MultiObjectiveOptimizer:
    """
    NSGA-II style multi-objective optimization.
    
    Supports multiple conflicting objectives (e.g., effectiveness vs efficiency
    vs novelty) and finds Pareto-optimal trade-offs.
    
    Features:
    - Non-dominated sorting
    - Crowding distance computation
    - Pareto front tracking
    - Tournament selection with rank + crowding
    """

    def __init__(self, objective_names: Optional[List[str]] = None):
        self.objective_names = objective_names or [
            "effectiveness", "efficiency", "novelty", "fuel_efficiency"
        ]
        self.pareto_fronts: List[List[int]] = []
        self._pareto_history: List[Dict[str, float]] = []

    def dominates(self, obj_a: MultiObjectiveFitness,
                  obj_b: MultiObjectiveFitness) -> bool:
        """Check if obj_a dominates obj_b (all objectives better or equal)."""
        better_in_any = False
        for name in self.objective_names:
            a_val = obj_a.objectives.get(name, 0.0)
            b_val = obj_b.objectives.get(name, 0.0)
            if a_val < b_val:
                return False  # obj_a is worse in at least one
            if a_val > b_val:
                better_in_any = True
        return better_in_any

    def non_dominated_sort(self, fitnesses: List[MultiObjectiveFitness]) -> List[List[int]]:
        """
        Perform non-dominated sorting.
        
        Returns:
            List of Pareto fronts (each front is a list of indices)
        """
        n = len(fitnesses)
        domination_count = [0] * n
        dominated_sets: List[List[int]] = [[] for _ in range(n)]
        fronts: List[List[int]] = [[]]
        
        for i in range(n):
            for j in range(n):
                if i == j:
                    continue
                if self.dominates(fitnesses[i], fitnesses[j]):
                    dominated_sets[i].append(j)
                elif self.dominates(fitnesses[j], fitnesses[i]):
                    domination_count[i] += 1
            
            if domination_count[i] == 0:
                fitnesses[i].rank = 0
                fronts[0].append(i)
        
        # Build subsequent fronts
        front_idx = 0
        while fronts[front_idx]:
            next_front = []
            for i in fronts[front_idx]:
                for j in dominated_sets[i]:
                    domination_count[j] -= 1
                    if domination_count[j] == 0:
                        fitnesses[j].rank = front_idx + 1
                        next_front.append(j)
            front_idx += 1
            fronts.append(next_front)
        
        # Remove empty last front
        if fronts and not fronts[-1]:
            fronts.pop()
        
        self.pareto_fronts = fronts
        return fronts

    def compute_crowding_distance(self, front: List[int],
                                  fitnesses: List[MultiObjectiveFitness]) -> None:
        """Compute crowding distance for individuals in a front."""
        m = len(front)
        if m <= 2:
            for i in front:
                fitnesses[i].crowding_distance = float("inf")
            return
        
        for i in front:
            fitnesses[i].crowding_distance = 0.0
        
        for name in self.objective_names:
            # Sort by objective
            front_sorted = sorted(front, key=lambda i: fitnesses[i].objectives.get(name, 0.0))
            
            # Boundaries get infinite distance
            fitnesses[front_sorted[0]].crowding_distance = float("inf")
            fitnesses[front_sorted[-1]].crowding_distance = float("inf")
            
            # Normalize objective range
            obj_range = (fitnesses[front_sorted[-1]].objectives.get(name, 0.0) -
                        fitnesses[front_sorted[0]].objectives.get(name, 0.0))
            if obj_range == 0:
                continue
            
            for k in range(1, m - 1):
                fitnesses[front_sorted[k]].crowding_distance += (
                    fitnesses[front_sorted[k + 1]].objectives.get(name, 0.0) -
                    fitnesses[front_sorted[k - 1]].objectives.get(name, 0.0)
                ) / obj_range

    def compute_fitness_from_telemetry(self, telemetry: Dict[str, Any]) -> MultiObjectiveFitness:
        """Compute multi-objective fitness from telemetry data."""
        mo = MultiObjectiveFitness()
        
        hits = telemetry.get("hits", 0)
        attempts = telemetry.get("attempts", 1)
        mo["effectiveness"] = hits / max(1, attempts)
        
        weapons_used = telemetry.get("weapons_used", 1)
        weapons_allocated = telemetry.get("weapons_allocated", 1)
        mo["efficiency"] = 1.0 - (weapons_used / max(1, weapons_allocated))
        
        actions_used = telemetry.get("actions_used", [])
        mo["novelty"] = min(1.0, len(set(actions_used)) / 10)
        
        fuel_consumed = telemetry.get("fuel_consumed", 0.0)
        mo["fuel_efficiency"] = max(0.0, 1.0 - fuel_consumed / 3.0)
        
        return mo

    def get_pareto_front_metrics(self) -> Dict[str, float]:
        """Get metrics about the current Pareto front."""
        if not self.pareto_fronts or not self.pareto_fronts[0]:
            return {}
        
        front_size = len(self.pareto_fronts[0])
        num_fronts = len(self.pareto_fronts)
        
        self._pareto_history.append({
            "front_size": front_size,
            "num_fronts": num_fronts,
            "timestamp": len(self._pareto_history),
        })
        
        return {
            "pareto_front_size": front_size,
            "num_fronts": num_fronts,
        }

    def get_stats(self) -> dict:
        return {
            "objectives": self.objective_names,
            "num_pareto_fronts": len(self.pareto_fronts),
            "pareto_front_size": len(self.pareto_fronts[0]) if self.pareto_fronts else 0,
            "pareto_history": len(self._pareto_history),
        }


# ── 7. Novelty Search with Behavioral Diversity ──────────────────

class NoveltySearch:
    """
    Novelty search algorithm that rewards behavioral diversity.
    
    Instead of optimizing for a single objective, novelty search rewards
    agents for exhibiting novel behaviors. This helps escape local optima
    and discover creative solutions.
    
    Features:
    - Behavior characterization (feature vector per genome)
    - Novelty computation via k-nearest neighbors
    - Novelty archive for long-term diversity
    - Adaptive novelty threshold
    """

    def __init__(self, archive_size: int = 100, k_nearest: int = 5,
                 novelty_threshold: float = 0.1):
        self.archive_size = archive_size
        self.k_nearest = k_nearest
        self.novelty_threshold = novelty_threshold
        self.archive: List[Dict[str, Any]] = []  # Stored behaviors
        self._novelty_scores: List[float] = []

    def characterize_behavior(self, genome: EvolutionaryGenome,
                             telemetry: Dict[str, Any]) -> List[float]:
        """Create a behavior characterization vector from genome + telemetry."""
        behavior = []
        
        # Action weights (normalized)
        for action in sorted(genome.action_weights.keys()):
            behavior.append(genome.action_weights.get(action, 0.0))
        
        # Phase parameters
        for phase in sorted(genome.phase_params.keys()):
            pp = genome.phase_params[phase]
            behavior.append(pp.speed)
            behavior.append(pp.confidence_threshold)
        
        # Telemetry features
        behavior.append(telemetry.get("hits", 0) / max(1, telemetry.get("attempts", 1)))
        behavior.append(telemetry.get("weapons_used", 0) / max(1, telemetry.get("weapons_allocated", 1)))
        
        # Normalize
        if behavior:
            max_val = max(behavior)
            if max_val > 0:
                behavior = [b / max_val for b in behavior]
        
        return behavior

    def compute_novelty(self, behavior: List[float]) -> float:
        """
        Compute novelty as average distance to k-nearest neighbors.
        
        Considers both the current population and the archive.
        """
        all_behaviors = [b["behavior"] for b in self.archive] + [behavior]
        
        if len(all_behaviors) < 2:
            self.archive.append({"behavior": behavior, "novelty": 1.0})
            return 1.0
        
        # Compute distances to all other behaviors
        distances = []
        for i, other in enumerate(all_behaviors[:-1]):  # Exclude self
            if other != behavior:
                dist = sum((a - b) ** 2 for a, b in zip(behavior, other)) ** 0.5
                distances.append(dist)
        
        distances.sort()
        k = min(self.k_nearest, len(distances))
        novelty = sum(distances[:k]) / max(1, k) if k > 0 else 0.0
        
        # Add to archive (if novel enough)
        if novelty > self.novelty_threshold:
            self.archive.append({
                "behavior": behavior,
                "novelty": novelty,
            })
            # Trim archive
            if len(self.archive) > self.archive_size:
                self.archive = self.archive[-self.archive_size:]
        
        self._novelty_scores.append(novelty)
        return novelty

    def compute_novelty_fitness(self, genome: EvolutionaryGenome,
                              telemetry: Dict[str, Any],
                              base_fitness: float = 0.0,
                              novelty_weight: float = 0.3) -> float:
        """
        Compute combined fitness with novelty bonus.
        
        fitness = (1 - novelty_weight) * base_fitness + novelty_weight * novelty_score
        """
        behavior = self.characterize_behavior(genome, telemetry)
        novelty = self.compute_novelty(behavior)
        return (1 - novelty_weight) * base_fitness + novelty_weight * novelty

    def get_stats(self) -> dict:
        return {
            "archive_size": len(self.archive),
            "avg_novelty": (sum(self._novelty_scores) / max(1, len(self._novelty_scores))
                          if self._novelty_scores else 0.0),
            "max_novelty": max(self._novelty_scores) if self._novelty_scores else 0.0,
            "novelty_threshold": self.novelty_threshold,
        }


# ── 8. Comprehensive Evolutionary Generator ──────────────────────

class ComprehensiveEvolutionaryGenerator:
    """
    Complete evolutionary system integrating all generative and evolutionary enhancements.
    
    Combines:
    - Generative Adversarial Coevolution (GAN-style)
    - Neural Topology Evolution (NEAT)
    - Evolutionary Strategy Optimization (NES)
    - Generative Tactical Variants
    - Enhanced Mutation
    - Multi-Objective Optimization
    - Novelty Search
    - Lamarckian Evolution
    """

    def __init__(self):
        self.adversarial_coevolution = GenerativeAdversarialCoevolution()
        self.neural_topology = NeuralTopologyEvolution()
        self.es_optimizer = EvolutionaryStrategyOptimizer()
        self.tactical_variants = GenerativeTacticalVariantEngine()
        self.mutation_operator = EnhancedMutationOperator()
        self.multi_objective = MultiObjectiveOptimizer()
        self.novelty_search = NoveltySearch()
        self._initialized = False

    def initialize(self) -> None:
        """Initialize all sub-systems."""
        self.neural_topology.initialize_population()
        self._initialized = True

    def generate_enhanced_coa(self, target_info: Dict[str, Any],
                             context: Optional[Dict[str, Any]] = None,
                             base_genome: Optional[EvolutionaryGenome] = None) -> Any:
        """
        Generate a COA using all evolutionary enhancements.
        
        Uses:
        1. Neural topology to determine action selection
        2. Tactical variants for pattern recombination
        3. Novelty search for exploration
        4. Multi-objective optimization for trade-offs
        """
        from .course_of_action import CourseOfAction
        
        if not self._initialized:
            self.initialize()
        
        domain = target_info.get("domain", "all")
        target_type = target_info.get("type", "unknown")
        constraints = context or {}
        
        # Get best patterns from tactical variant engine
        best_patterns = self.tactical_variants.get_best_patterns(3)
        
        if best_patterns and len(best_patterns) >= 2:
            # Recombine two best patterns
            parent_a = best_patterns[0]
            parent_b = best_patterns[1]
            if random.random() < 0.7:
                pattern = self.tactical_variants.recombine_patterns(parent_a, parent_b)
            else:
                pattern = self.tactical_variants.generate_novel_variant(
                    parent_a, {"domain": domain}
                )
        else:
            # Generate from scratch
            base = {
                "phases": ["locate", "track", "engage", "assess"],
                "novelty": 0.5,
                "success_rate": 0.5,
            }
            pattern = self.tactical_variants.generate_novel_variant(
                base, {"domain": domain}
            )
        
        phases = pattern.get("phases", ["locate", "engage", "assess"])
        novelty = pattern.get("novelty", 0.5)
        
        # Apply Lamarckian learning if base genome provided
        if base_genome and context:
            self.mutation_operator.apply_lamarckian(base_genome, context)
        
        coa = CourseOfAction(
            coa_id=f"COA-ENHANCED-{random.randint(1000, 9999)}",
            name="Enhanced Evolutionary COA",
            description=f"Generative-evolutionary COA for {domain}/{target_type}",
            domain=domain,
            phases=phases,
            required_assets=[],
            estimated_time_ms=random.uniform(10000, 100000),
            risk_level=random.uniform(0.2, 0.8),
            novelty_score=novelty,
        )
        
        return coa

    def update_fitness(self, genome: EvolutionaryGenome,
                      telemetry: Dict[str, Any]) -> Dict[str, float]:
        """
        Update all evolutionary components with fitness feedback.
        
        Returns:
            Dict with fitness components
        """
        # Base fitness
        base_fitness = 0.5  # Simplified
        
        # Multi-objective fitness
        mo_fitness = self.multi_objective.compute_fitness_from_telemetry(telemetry)
        
        # Novelty search
        novelty_fitness = self.novelty_search.compute_novelty_fitness(
            genome, telemetry, base_fitness, novelty_weight=0.3
        )
        
        return {
            "base_fitness": base_fitness,
            "effectiveness": mo_fitness["effectiveness"],
            "efficiency": mo_fitness["efficiency"],
            "novelty": mo_fitness["novelty"],
            "novelty_search_fitness": novelty_fitness,
        }

    def get_stats(self) -> dict:
        return {
            "adversarial": self.adversarial_coevolution.get_stats(),
            "neural_topology": self.neural_topology.get_stats(),
            "es_optimizer": self.es_optimizer.get_stats(),
            "tactical_variants": self.tactical_variants.get_stats(),
            "mutation_operator": self.mutation_operator.get_stats(),
            "multi_objective": self.multi_objective.get_stats(),
            "novelty_search": self.novelty_search.get_stats(),
        }
