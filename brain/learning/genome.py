# Copyright (c) Ultrone Contributors. All rights reserved.
"""
Genome Evolution Protocol (GEP) Engine
=======================================
Treats parts of an AI agent's logic as "genes" and "capsules" with
mutation, selection, and cross-generation testing for autonomous adaptation.

Extended with military warhead capsules for domain-specific evolution.
"""

import copy
import random
import json
import logging
from typing import Dict, List, Optional, Tuple, Any, Callable
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime

logger = logging.getLogger("Ultrone.Brain.Learning.Genome")

# ── Strategies ──

class MutationStrategy(Enum):
    """Strategies for gene mutation."""
    UNIFORM = "uniform"           # Random perturbation within bounds
    GAUSSIAN = "gaussian"         # Gaussian noise centered on current value
    SWAP = "swap"                 # Swap values between two genes
    RESET = "reset"               # Reset to initial/default value
    ADAPTIVE = "adaptive"         # Mutation rate adapts based on fitness


class CrossoverStrategy(Enum):
    """Strategies for combining parent genomes."""
    SINGLE_POINT = "single_point"
    TWO_POINT = "two_point"
    UNIFORM = "uniform"
    BLEND = "blend"               # Weighted average for continuous genes


class SelectionStrategy(Enum):
    """Strategies for selecting genomes for reproduction."""
    TOURNAMENT = "tournament"
    ROULETTE_WHEEL = "roulette_wheel"
    RANK_BASED = "rank_based"
    ELITIST = "elitist"           # Keep top N unchanged


# ── Core Data Structures ──

@dataclass
class Gene:
    """
    A single evolvable parameter in the agent's genome.
    
    ``capsule`` groups related genes together (e.g., "air_defense", "cyber_jamming").
    """
    name: str
    value: float = 0.0
    min_value: float = 0.0
    max_value: float = 1.0
    mutation_rate: float = 0.15
    description: str = ""
    capsule: str = "general"       # Capsule grouping
    frozen: bool = False           # If True, never mutate this gene
    
    def clone(self) -> "Gene":
        return Gene(
            name=self.name,
            value=self.value,
            min_value=self.min_value,
            max_value=self.max_value,
            mutation_rate=self.mutation_rate,
            description=self.description,
            capsule=self.capsule,
            frozen=self.frozen,
        )
    
    def mutate(self, strategy: MutationStrategy = MutationStrategy.GAUSSIAN) -> bool:
        """Mutate this gene's value in-place. Returns True if changed."""
        if self.frozen:
            return False
        
        old_value = self.value
        
        if strategy == MutationStrategy.UNIFORM:
            self.value = random.uniform(self.min_value, self.max_value)
        elif strategy == MutationStrategy.GAUSSIAN:
            sigma = (self.max_value - self.min_value) * 0.1
            noise = random.gauss(0, sigma)
            self.value = self.value + noise
        elif strategy == MutationStrategy.RESET:
            self.value = (self.max_value + self.min_value) / 2
        elif strategy == MutationStrategy.ADAPTIVE:
            # Adaptive: scale mutation rate by current value's position in range
            range_size = self.max_value - self.min_value
            if range_size > 0:
                position = (self.value - self.min_value) / range_size
                adaptive_rate = self.mutation_rate * (1.0 + abs(position - 0.5))
                if random.random() < adaptive_rate:
                    sigma = range_size * 0.15 * adaptive_rate
                    self.value += random.gauss(0, sigma)
        
        # Clamp to bounds
        self.value = max(self.min_value, min(self.max_value, self.value))
        self.value = round(self.value, 6)
        
        return abs(self.value - old_value) > 1e-9
    
    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "value": self.value,
            "min_value": self.min_value,
            "max_value": self.max_value,
            "mutation_rate": self.mutation_rate,
            "description": self.description,
            "capsule": self.capsule,
            "frozen": self.frozen,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "Gene":
        return cls(**{k: v for k, v in data.items() if k in 
                      ["name", "value", "min_value", "max_value", "mutation_rate",
                       "description", "capsule", "frozen"]})


@dataclass
class Capsule:
    """
    A logical grouping of related genes that form a functional unit.
    
    Capsules can be evolved, swapped, or transferred between agents
    like biological organelles.
    """
    name: str
    genes: List[Gene] = field(default_factory=list)
    description: str = ""
    fitness_contribution: float = 0.0
    is_active: bool = True
    
    def add_gene(self, gene: Gene) -> None:
        gene.capsule = self.name
        self.genes.append(gene)
    
    def get_gene(self, name: str) -> Optional[Gene]:
        for g in self.genes:
            if g.name == name:
                return g
        return None
    
    def mutate_all(self, strategy: MutationStrategy = MutationStrategy.GAUSSIAN) -> int:
        """Mutate all non-frozen genes. Returns count of mutations."""
        count = 0
        for gene in self.genes:
            if random.random() < gene.mutation_rate:
                if gene.mutate(strategy):
                    count += 1
        return count
    
    def clone(self) -> "Capsule":
        return Capsule(
            name=self.name,
            genes=[g.clone() for g in self.genes],
            description=self.description,
            fitness_contribution=self.fitness_contribution,
            is_active=self.is_active,
        )
    
    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "genes": [g.to_dict() for g in self.genes],
            "description": self.description,
            "fitness_contribution": self.fitness_contribution,
            "is_active": self.is_active,
        }


@dataclass
class Genome:
    """
    Complete genetic blueprint of an agent.
    
    Contains all capsules and their genes. The genome represents
    the entire evolvable configuration of an agent's behavior.
    """
    generation: int = 0
    capsules: Dict[str, Capsule] = field(default_factory=dict)
    fitness_score: float = 0.0
    fitness_history: List[float] = field(default_factory=list)
    agent_id: str = ""
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    parent_genome_id: Optional[str] = None
    
    def add_capsule(self, capsule: Capsule) -> None:
        self.capsules[capsule.name] = capsule
    
    def get_capsule(self, name: str) -> Optional[Capsule]:
        return self.capsules.get(name)
    
    def get_all_genes(self) -> List[Gene]:
        genes = []
        for capsule in self.capsules.values():
            genes.extend(capsule.genes)
        return genes
    
    def get_gene(self, name: str) -> Optional[Gene]:
        for capsule in self.capsules.values():
            gene = capsule.get_gene(name)
            if gene:
                return gene
        return None
    
    def mutate(self, strategy: MutationStrategy = MutationStrategy.GAUSSIAN) -> int:
        """Mutate all capsules. Returns total mutation count."""
        count = 0
        for capsule in self.capsules.values():
            if capsule.is_active:
                count += capsule.mutate_all(strategy)
        return count
    
    def clone(self) -> "Genome":
        new = Genome(
            generation=self.generation + 1,
            capsules={k: v.clone() for k, v in self.capsules.items()},
            fitness_score=0.0,
            fitness_history=list(self.fitness_history),
            agent_id=self.agent_id,
            created_at=datetime.utcnow().isoformat(),
            parent_genome_id=self.agent_id or None,
        )
        return new
    
    def to_dict(self) -> dict:
        return {
            "generation": self.generation,
            "capsules": {k: v.to_dict() for k, v in self.capsules.items()},
            "fitness_score": self.fitness_score,
            "fitness_history": self.fitness_history,
            "agent_id": self.agent_id,
            "created_at": self.created_at,
            "parent_genome_id": self.parent_genome_id,
        }
    
    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2, ensure_ascii=False)


# ── Genome Engine ──

class GenomeEngine:
    """
    The core evolution engine implementing the Genome Evolution Protocol.
    
    Features:
    - Multiple mutation strategies (uniform, gaussian, adaptive, swap, reset)
    - Crossover between parent genomes
    - Tournament and fitness-proportional selection
    - Sandbox validation before deployment
    - Fitness history tracking
    """
    
    def __init__(
        self,
        initial_genome: Optional[Genome] = None,
        mutation_strategy: MutationStrategy = MutationStrategy.ADAPTIVE,
        crossover_strategy: CrossoverStrategy = CrossoverStrategy.BLEND,
        selection_strategy: SelectionStrategy = SelectionStrategy.TOURNAMENT,
        tournament_size: int = 3,
        elitism_count: int = 2,
        population_size: int = 10,
        min_acceptable_fitness: float = 0.75,
    ):
        self.mutation_strategy = mutation_strategy
        self.crossover_strategy = crossover_strategy
        self.selection_strategy = selection_strategy
        self.tournament_size = tournament_size
        self.elitism_count = elitism_count
        self.population_size = population_size
        self.min_acceptable_fitness = min_acceptable_fitness
        
        self.population: List[Genome] = []
        self.generation = 0
        self.active_genome: Optional[Genome] = initial_genome
        self.best_genome: Optional[Genome] = None
        self.best_fitness: float = 0.0
        
        if initial_genome:
            self.population.append(initial_genome)
        
        self.sandbox_validators: List[Callable[[Genome], bool]] = []
        self._fitness_history: List[float] = []
    
    def register_sandbox_validator(self, validator: Callable[[Genome], bool]) -> None:
        """Register a validation function that checks genome sanity before deployment."""
        self.sandbox_validators.append(validator)
    
    def _validate_in_sandbox(self, genome: Genome) -> bool:
        """Run all sandbox validators. All must pass."""
        if not self.sandbox_validators:
            return True
        return all(v(genome) for v in self.sandbox_validators)
    
    def record_fitness(self, fitness: float) -> dict:
        """
        Record a fitness measurement for the active genome.
        Triggers evolution cycle if enough measurements accumulated.
        """
        self._fitness_history.append(fitness)
        self.active_genome.fitness_history.append(fitness)
        
        avg_fitness = sum(self._fitness_history) / len(self._fitness_history)
        
        if len(self._fitness_history) >= 5:
            self._evaluate_and_evolve()
        
        return {
            "fitness": fitness,
            "average_fitness": avg_fitness,
            "generation": self.generation,
        }
    
    def _evaluate_and_evolve(self) -> Optional[Genome]:
        """Evaluate current fitness and trigger evolution if below threshold."""
        if not self._fitness_history:
            return None
        
        avg_fitness = sum(self._fitness_history) / len(self._fitness_history)
        
        if self.active_genome:
            self.active_genome.fitness_score = avg_fitness
            if avg_fitness > self.best_fitness and self.active_genome:
                self.best_fitness = avg_fitness
                self.best_genome = self.active_genome.clone()
        
        logger.info(
            "📊 Performance Telemetry -> Avg Fitness: %.3f (Target: >= %.3f, Gen: %d)",
            avg_fitness, self.min_acceptable_fitness, self.generation,
        )
        
        if avg_fitness < self.min_acceptable_fitness:
            logger.warning("🚨 Fitness below threshold. Initiating genome evolution cycle...")
            new_genome = self.evolve()
            self._fitness_history.clear()
            return new_genome
        
        logger.info("✅ Fitness stable. Retaining current genome.")
        self._fitness_history.clear()
        return None
    
    def evolve(self) -> Optional[Genome]:
        """
        Run one full evolution cycle:
        1. Generate offspring via mutation/crossover
        2. Validate in sandbox
        3. Select best genome
        4. Deploy
        """
        if not self.active_genome:
            return None
        
        # Generate offspring
        candidates = []
        
        # 1. Mutated clones
        for i in range(self.population_size):
            candidate = self.active_genome.clone()
            mutations = candidate.mutate(self.mutation_strategy)
            if mutations > 0 and self._validate_in_sandbox(candidate):
                candidates.append(candidate)
        
        # 2. Crossovers with best genome if available
        if self.best_genome and self.crossover_strategy != CrossoverStrategy.BLEND:
            for i in range(min(3, self.population_size // 2)):
                child = self._crossover(self.active_genome, self.best_genome)
                if child and self._validate_in_sandbox(child):
                    candidates.append(child)
        
        if not candidates:
            logger.warning("No valid candidates generated in evolution cycle")
            return None
        
        # Select best candidate
        best_candidate = self._select_best(candidates)
        
        if not best_candidate:
            return None
        
        # Deploy
        self.generation += 1
        best_candidate.generation = self.generation
        self.active_genome = best_candidate
        self.population.append(best_candidate)
        
        # Keep population size bounded
        if len(self.population) > self.population_size * 2:
            self.population = self.population[-self.population_size:]
        
        logger.info(
            "🚀 New genome deployed: Generation %d | Fitness: %.3f | Capsules: %d | Genes: %d",
            self.generation, best_candidate.fitness_score,
            len(best_candidate.capsules), len(best_candidate.get_all_genes()),
        )
        
        return best_candidate
    
    def _crossover(self, parent1: Genome, parent2: Genome) -> Optional[Genome]:
        """Create a child genome by blending genes from two parents."""
        child = parent1.clone()
        child.parent_genome_id = f"{parent1.agent_id or 'p1'}+{parent2.agent_id or 'p2'}"
        
        if self.crossover_strategy == CrossoverStrategy.BLEND:
            for capsule_name, capsule in child.capsules.items():
                parent2_capsule = parent2.capsules.get(capsule_name)
                if not parent2_capsule or not capsule.is_active:
                    continue
                for i, gene in enumerate(capsule.genes):
                    p2_gene = parent2_capsule.get_gene(gene.name)
                    if p2_gene and not gene.frozen:
                        alpha = random.uniform(0.3, 0.7)
                        gene.value = round(alpha * gene.value + (1 - alpha) * p2_gene.value, 6)
                        gene.value = max(gene.min_value, min(gene.max_value, gene.value))
        
        elif self.crossover_strategy == CrossoverStrategy.UNIFORM:
            for capsule_name, capsule in child.capsules.items():
                parent2_capsule = parent2.capsules.get(capsule_name)
                if not parent2_capsule or not capsule.is_active:
                    continue
                for gene in capsule.genes:
                    if not gene.frozen and random.random() < 0.5:
                        p2_gene = parent2_capsule.get_gene(gene.name)
                        if p2_gene:
                            gene.value = p2_gene.value
        
        return child
    
    def _select_best(self, candidates: List[Genome]) -> Optional[Genome]:
        """Select the best genome from candidates using the configured strategy."""
        if not candidates:
            return None
        
        if self.selection_strategy == SelectionStrategy.ELITIST:
            scored = [(g, g.fitness_score) for g in candidates]
            scored.sort(key=lambda x: x[1], reverse=True)
            return scored[0][0]
        
        elif self.selection_strategy == SelectionStrategy.TOURNAMENT:
            best = None
            best_fitness = -float('inf')
            sample = random.sample(candidates, min(self.tournament_size, len(candidates)))
            for g in sample:
                if g.fitness_score > best_fitness:
                    best_fitness = g.fitness_score
                    best = g
            return best
        
        elif self.selection_strategy == SelectionStrategy.ROULETTE_WHEEL:
            total = sum(max(0.01, g.fitness_score) for g in candidates)
            pick = random.uniform(0, total)
            current = 0
            for g in candidates:
                current += max(0.01, g.fitness_score)
                if current >= pick:
                    return g
            return candidates[-1]
        
        else:
            # Default: pick the one with most mutations (highest potential)
            candidates.sort(key=lambda g: len(g.get_all_genes()), reverse=True)
            return candidates[0]
    
    def create_default_genome(self, agent_id: str = "ultrone-agent") -> Genome:
        """Create a default genome with standard capsules for multi-domain operations."""
        genome = Genome(agent_id=agent_id)
        
        # ── Air Defense Capsule ──
        air_defense = Capsule("air_defense", description="Air engagement parameters")
        air_defense.add_gene(Gene("interceptor_range_km", 150.0, 50.0, 500.0, 0.15, "Max intercept range"))
        air_defense.add_gene(Gene("missile_lead_factor", 1.4, 0.5, 3.0, 0.12, "Missile pursuit aggressiveness"))
        air_defense.add_gene(Gene("swarm_dispersion_m", 150.0, 50.0, 500.0, 0.10, "Drone swarm spread"))
        air_defense.add_gene(Gene("altitude_advantage_m", 3000.0, 500.0, 10000.0, 0.15, "Preferred altitude advantage"))
        genome.add_capsule(air_defense)
        
        # ── Cyber Warfare Capsule ──
        cyber = Capsule("cyber_warfare", description="Cyber and electronic warfare parameters")
        cyber.add_gene(Gene("jamming_intensity", 0.85, 0.1, 1.0, 0.12, "ECM jamming power"))
        cyber.add_gene(Gene("frequency_hopping_rate", 0.7, 0.1, 1.0, 0.10, "Frequency agility"))
        cyber.add_gene(Gene("spoofing_confidence", 0.6, 0.1, 1.0, 0.15, "Signal spoofing aggression"))
        genome.add_capsule(cyber)
        
        # ── Ground Operations Capsule ──
        ground = Capsule("ground_operations", description="Land/sea domain parameters")
        ground.add_gene(Gene("defensive_angle_deg", 45.0, 15.0, 90.0, 0.10, "Armor defensive posture"))
        ground.add_gene(Gene("engagement_delay_s", 0.2, 0.05, 2.0, 0.08, "Reaction time delay"))
        ground.add_gene(Gene("patrol_coverage_km", 50.0, 10.0, 200.0, 0.12, "Patrol area radius"))
        genome.add_capsule(ground)
        
        # ── Decision Making Capsule ──
        decision = Capsule("decision_making", description="Command and control parameters")
        decision.add_gene(Gene("aggression_threshold", 0.6, 0.1, 1.0, 0.10, "Threshold for offensive action"))
        decision.add_gene(Gene("risk_tolerance", 0.4, 0.1, 1.0, 0.12, "Willingness to accept risk"))
        decision.add_gene(Gene("resource_conservation", 0.7, 0.1, 1.0, 0.10, "Resource preservation priority"))
        decision.add_gene(Gene("intel_weighting", 0.8, 0.3, 1.0, 0.08, "Trust in intelligence data"))
        genome.add_capsule(decision)
        
        # ── Learning & Adaptation Capsule ──
        learning = Capsule("learning_adaptation", description="Self-improvement parameters")
        learning.add_gene(Gene("memory_retention", 0.85, 0.3, 1.0, 0.10, "Rate of experience retention"))
        learning.add_gene(Gene("pattern_sensitivity", 0.7, 0.2, 1.0, 0.12, "Sensitivity to pattern detection"))
        learning.add_gene(Gene("innovation_rate", 0.3, 0.05, 0.8, 0.15, "Willingness to try novel strategies"))
        learning.add_gene(Gene("crossover_learning", 0.5, 0.1, 1.0, 0.12, "Cross-domain knowledge transfer"))
        genome.add_capsule(learning)
        
        # ── Naval Warfare Capsule ──
        naval = Capsule("naval_warfare", description="Naval engagement parameters")
        naval.add_gene(Gene("engagement_range_nm", 50.0, 10.0, 200.0, 0.12, "Naval weapon range in nautical miles"))
        naval.add_gene(Gene("torpedo_closing_speed", 40.0, 20.0, 80.0, 0.15, "Torpedo approach speed knots"))
        naval.add_gene(Gene("sonar_sensitivity", 0.8, 0.3, 1.0, 0.10, "Submarine detection sensitivity"))
        naval.add_gene(Gene("decoy_effectiveness", 0.6, 0.2, 0.9, 0.12, "Decoy countermeasure effectiveness"))
        genome.add_capsule(naval)
        
        # ── Space Operations Capsule ──
        space = Capsule("space_operations", description="Orbital/space engagement parameters")
        space.add_gene(Gene("orbital_period_min", 90.0, 60.0, 180.0, 0.10, "Satellite orbital period minutes"))
        space.add_gene(Gene("sensor_resolution_m", 0.5, 0.1, 5.0, 0.15, "Optical sensor resolution in meters"))
        space.add_gene(Gene("deorbit_precision", 0.9, 0.5, 1.0, 0.08, "Precision of deorbit maneuvers"))
        space.add_gene(Gene("power_management", 0.7, 0.3, 1.0, 0.12, "Power conservation priority"))
        genome.add_capsule(space)
        
        # ── Kill Chain Efficiency Capsule ──
        kill_chain = Capsule("kill_chain_efficiency", description="F2T2EA optimization parameters")
        kill_chain.add_gene(Gene("f2t2ea_phase_speed", 0.8, 0.3, 1.0, 0.15, "Speed of kill chain phase transitions"))
        kill_chain.add_gene(Gene("target_confirmation_threshold", 0.7, 0.5, 0.99, 0.10, "Confidence needed for target ID"))
        kill_chain.add_gene(Gene("bda_rigor", 0.85, 0.5, 1.0, 0.12, "Battle Damage Assessment thoroughness"))
        kill_chain.add_gene(Gene("reengage_decision_speed", 2.0, 0.5, 10.0, 0.15, "Seconds between re-engagement checks"))
        genome.add_capsule(kill_chain)
        
        self.active_genome = genome
        self.population = [genome]
        return genome
    
    def get_stats(self) -> dict:
        return {
            "generation": self.generation,
            "population_size": len(self.population),
            "best_fitness": self.best_fitness,
            "min_acceptable_fitness": self.min_acceptable_fitness,
            "active_capsules": len(self.active_genome.capsules) if self.active_genome else 0,
            "active_genes": len(self.active_genome.get_all_genes()) if self.active_genome else 0,
            "mutation_strategy": self.mutation_strategy.value,
            "crossover_strategy": self.crossover_strategy.value,
            "selection_strategy": self.selection_strategy.value,
        }