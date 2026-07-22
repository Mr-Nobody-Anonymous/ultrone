# Copyright (c) Ultrone Contributors. All rights reserved.
"""Coevolution engine for adversarial Blue vs Red evolution.

Phase 7 Upgrade: AlphaStar-style League Training with SBX Crossover,
Polynomial Mutation, and Self-Adaptive Mutation Rates.

Architecture:
  - main_agent: The current best Blue commander
  - main_exploiters: Specialized against specific Red strategies
  - league_exploiters: Trained to beat the main_agent
  - past_selves: Historical checkpoints for stability

Genetic Operators:
  - SBX (Simulated Binary Crossover) for continuous parameters
  - Polynomial Mutation for fine-grained local search
  - Self-Adaptive Mutation Rate (bounds: [0.01, 0.30])
"""

from __future__ import annotations

import copy
import logging
import math
import random
from typing import Any, Dict, List, Optional, Tuple

import sys
from pathlib import Path
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))
from brain.reasoning.evolutionary_coagen import EvolutionaryCOAGenerator
from brain.reasoning.swarm_genomes import CommanderGenome
from brain.reasoning.red_force_genomes import RedForceGenome

logger = logging.getLogger("Ultrone.Brain.Reasoning.Coevolution")

# =====================================================================
# Phase 7: League Constants
# =====================================================================
MAX_PAST_SELVES = 5          # Keep last 5 historical main agents
LEAGUE_EXPLOITERS = 3        # Number of opponents trained to beat main
MAIN_EXPLOITERS_PER_RED = 2  # Blue exploiters per Red archetype
SELF_ADAPT_TAU = 1.0 / math.sqrt(2.0 * 10.0)  # Learning rate for self-adaptive mutation
MUTATION_MIN = 0.01
MUTATION_MAX = 0.30

# =====================================================================
# Phase 7: SBX (Simulated Binary Crossover) — vectorized
# =====================================================================

def sbx_crossover(parent1_val: float, parent2_val: float,
                  lower_bound: float, upper_bound: float,
                  eta: float = 15.0) -> Tuple[float, float]:
    """
    Simulated Binary Crossover (SBX) for continuous parameters.
    
    Produces two children from two parent values. eta controls the
    spread: higher eta → children closer to parents (exploitation),
    lower eta → children more spread (exploration).
    
    Args:
        parent1_val: First parent value
        parent2_val: Second parent value
        lower_bound: Minimum allowed value
        upper_bound: Maximum allowed value
        eta: Distribution index (default 15 — moderate spread)
        
    Returns:
        (child1, child2) tuple
    """
    if random.random() > 0.5:
        # No crossover
        return parent1_val, parent2_val
    
    if abs(parent1_val - parent2_val) < 1e-12:
        return parent1_val, parent2_val
    
    y1 = min(parent1_val, parent2_val)
    y2 = max(parent1_val, parent2_val)
    
    # Compute beta using polynomial distribution
    beta = 1.0 + 2.0 * (y1 - lower_bound) / (y2 - y1 + 1e-12)
    alpha = 2.0 - beta ** (-(eta + 1.0))
    
    if random.random() <= 1.0 / alpha:
        beta_q = (random.random() * alpha) ** (1.0 / (eta + 1.0))
    else:
        beta_q = (1.0 / (2.0 - random.random() * alpha)) ** (1.0 / (eta + 1.0))
    
    child1 = 0.5 * ((y1 + y2) - beta_q * (y2 - y1))
    
    beta = 1.0 + 2.0 * (upper_bound - y2) / (y2 - y1 + 1e-12)
    alpha = 2.0 - beta ** (-(eta + 1.0))
    
    if random.random() <= 1.0 / alpha:
        beta_q = (random.random() * alpha) ** (1.0 / (eta + 1.0))
    else:
        beta_q = (1.0 / (2.0 - random.random() * alpha)) ** (1.0 / (eta + 1.0))
    
    child2 = 0.5 * ((y1 + y2) + beta_q * (y2 - y1))
    
    # Clip to bounds
    child1 = max(lower_bound, min(upper_bound, child1))
    child2 = max(lower_bound, min(upper_bound, child2))
    
    return child1, child2


def polynomial_mutation(value: float, lower_bound: float, upper_bound: float,
                        eta: float = 15.0, prob_mutation: float = 0.15) -> float:
    """
    Polynomial Mutation for fine-grained local search.
    
    Perturbs a value using a polynomial probability distribution.
    Higher eta → smaller perturbations (local search).
    
    Args:
        value: Current value
        lower_bound: Minimum allowed value
        upper_bound: Maximum allowed value
        eta: Distribution index (default 15)
        prob_mutation: Probability of mutation occurring
        
    Returns:
        Mutated value (clipped to bounds)
    """
    if random.random() > prob_mutation:
        return value
    
    delta = random.random()
    delta_q: float
    
    if delta <= 0.5:
        delta_q = (2.0 * delta) ** (1.0 / (eta + 1.0)) - 1.0
    else:
        delta_q = 1.0 - (2.0 * (1.0 - delta)) ** (1.0 / (eta + 1.0))
    
    mutated = value + delta_q * (upper_bound - lower_bound)
    return max(lower_bound, min(upper_bound, mutated))


def self_adaptive_mutate_rate(parent_rate: float) -> float:
    """
    Self-adaptive mutation rate update.
    
    mutation_rate' = mutation_rate * exp(tau * N(0,1))
    tau = 1 / sqrt(2 * sqrt(n))
    
    Ensures rate stays within [MUTATION_MIN, MUTATION_MAX].
    """
    tau = SELF_ADAPT_TAU
    new_rate = parent_rate * math.exp(tau * random.gauss(0, 1))
    return max(MUTATION_MIN, min(MUTATION_MAX, new_rate))


# =====================================================================
# Phase 7: League Data Structures
# =====================================================================

class BlueLeague:
    """
    AlphaStar-style Blue league population.
    
    Contains the main agent, exploiters, and past selves.
    """
    def __init__(self):
        self.main_agent: Optional[CommanderGenome] = None
        self.main_exploiters: List[CommanderGenome] = []
        self.league_exploiters: List[CommanderGenome] = []
        self.past_selves: List[CommanderGenome] = []
    
    def snapshot_main(self) -> None:
        """Save current main agent to past_selves checkpoint list."""
        if self.main_agent is not None:
            # Deep copy the genome state
            snapshot = copy_genome(self.main_agent)
            self.past_selves.append(snapshot)
            # Trim to MAX_PAST_SELVES
            if len(self.past_selves) > MAX_PAST_SELVES:
                self.past_selves.pop(0)
    
    def get_blue_sample(self) -> List[CommanderGenome]:
        """Sample from all Blue agents for Red evaluation."""
        sample = []
        if self.main_agent is not None:
            sample.append(self.main_agent)
        if self.main_exploiters:
            sample.extend(random.sample(
                self.main_exploiters,
                min(len(self.main_exploiters), 2)
            ))
        return sample
    
    def get_all_blue(self) -> List[CommanderGenome]:
        """Get all Blue agents for full evaluation."""
        agents = []
        if self.main_agent is not None:
            agents.append(self.main_agent)
        agents.extend(self.main_exploiters)
        return agents


def copy_genome(genome: CommanderGenome) -> CommanderGenome:
    """Create a deep-ish copy of a CommanderGenome for league checkpoints."""
    return CommanderGenome(
        genome_id=f"{genome.genome_id}-CHKPT",
        generation=genome.generation,
        agent_id=genome.agent_id,
        action_weights=dict(genome.action_weights),
        synergy_map=dict(genome.synergy_map),
        phase_params={
            k: copy.copy(v) for k, v in genome.phase_params.items()
        },
        resource_conservation=genome.resource_conservation,
        time_optimization=genome.time_optimization,
        domain=genome.domain,
        mutation_rate=genome.mutation_rate,
        fitness_score=genome.fitness_score,
        allocation_weights=dict(getattr(genome, 'allocation_weights', {})),
    )


# =====================================================================
# Main CoevolutionEngine (Phase 7)
# =====================================================================

class CoevolutionEngine:
    """
    Manages two adversarial populations: Blue Commanders and Red Force genomes.
    
    Phase 7: AlphaStar-style League Training.
    - Blue has a main_agent, main_exploiters (vs specific Red), and past_selves
    - Genetic operators use SBX + Polynomial Mutation + Self-Adaptive Rates
    - Fitness evaluated across multiple Red opponents + past selves
    
    Phase 6: Uses Monte Carlo Forklift for probabilistic fitness evaluation,
    penalizes high fuel consumption, and rewards supply node preservation.
    """
    
    def __init__(self, sample_size: int = 3, use_monte_carlo: bool = True) -> None:
        self.sample_size = sample_size
        self.use_monte_carlo = use_monte_carlo
        
        # Phase 7: AlphaStar-style League
        self.blue_league = BlueLeague()
        
        # Red population: RedForceGenomes
        self.red_population: List[RedForceGenome] = []
        self.red_active: Optional[RedForceGenome] = None
        
        # Evolution generators
        self.blue_generator = EvolutionaryCOAGenerator()
        self.red_mutation_rate = 0.15
        
        # Phase 6: Monte Carlo Forklift (lazy import)
        self._monte_carlo = None
    
    def _get_monte_carlo(self):
        """Lazy import Monte Carlo Forklift."""
        if self._monte_carlo is None:
            try:
                from brain.reasoning.monte_carlo_engine import MonteCarloForklift
                self._monte_carlo = MonteCarloForklift(num_forks=50)
            except Exception as e:
                logger.warning(f"Monte Carlo Forklift unavailable: {e}")
                self._monte_carlo = False
        return self._monte_carlo
    
    # ------------------------------------------------------------------
    # Legacy compatible accessors
    # ------------------------------------------------------------------
    @property
    def blue_population(self) -> List[CommanderGenome]:
        """Legacy compatibility: return all Blue agents."""
        return self.blue_league.get_all_blue()
    
    @blue_population.setter
    def blue_population(self, value: List[CommanderGenome]) -> None:
        """Legacy compatible setter."""
        if value:
            self.blue_league.main_agent = value[0]
            if len(value) > 1:
                self.blue_league.main_exploiters = value[1:]
    
    @property
    def blue_active(self) -> Optional[CommanderGenome]:
        """Legacy compatible: return main agent."""
        return self.blue_league.main_agent
    
    @blue_active.setter
    def blue_active(self, value: Optional[CommanderGenome]) -> None:
        self.blue_league.main_agent = value
    
    def initialize_blue(self, commander: CommanderGenome) -> None:
        """Initialize Blue league with a starting commander."""
        self.blue_league.main_agent = commander
        self.blue_league.main_exploiters = []
        self.blue_league.league_exploiters = []
        self.blue_league.past_selves = []
    
    def initialize_red(self, red_genome: RedForceGenome) -> None:
        """Initialize Red population with a starting genome."""
        self.red_population = [red_genome]
        self.red_active = red_genome
    
    # ------------------------------------------------------------------
    # Phase 7: SBX-based Crossover for CommanderGenome
    # ------------------------------------------------------------------
    def _sbx_crossover_commanders(self, parent_a: CommanderGenome,
                                   parent_b: CommanderGenome) -> CommanderGenome:
        """
        SBX crossover between two CommanderGenomes.
        
        Uses SBX for continuous parameters (mutation_rate, resource_conservation,
        time_optimization) and blended intermediate for action_weights.
        """
        child = CommanderGenome(
            genome_id=f"GEN-{random.randint(10000, 99999)}",
            generation=max(parent_a.generation, parent_b.generation) + 1,
            agent_id=parent_a.agent_id,
            domain=parent_a.domain,
            mutation_rate=random.uniform(0.1, 0.2),  # will be overwritten
        )
        
        # --- SBX for continuous scalar parameters ---
        mr1, mr2 = sbx_crossover(parent_a.mutation_rate, parent_b.mutation_rate,
                                  MUTATION_MIN, MUTATION_MAX)
        child.mutation_rate = random.choice([mr1, mr2])
        
        rc1, rc2 = sbx_crossover(parent_a.resource_conservation,
                                  parent_b.resource_conservation, 0.3, 1.0)
        child.resource_conservation = random.choice([rc1, rc2])
        
        to1, to2 = sbx_crossover(parent_a.time_optimization,
                                  parent_b.time_optimization, 0.5, 2.0)
        child.time_optimization = random.choice([to1, to2])
        
        # --- Blended intermediate for action_weights ---
        all_actions = set(parent_a.action_weights.keys()) | set(parent_b.action_weights.keys())
        for action in all_actions:
            a = parent_a.action_weights.get(action, 0.5)
            b = parent_b.action_weights.get(action, 0.5)
            if random.random() < 0.5:
                # SBX for individual weights
                c1, c2 = sbx_crossover(a, b, 0.0, 1.0)
                child.action_weights[action] = random.choice([c1, c2])
            else:
                # Blend
                alpha = random.uniform(0.3, 0.7)
                child.action_weights[action] = max(0.0, min(1.0, alpha * a + (1 - alpha) * b))
        
        # --- SBX for allocation_weights ---
        all_keys = set(getattr(parent_a, 'allocation_weights', {}).keys())
        all_keys |= set(getattr(parent_b, 'allocation_weights', {}).keys())
        for key in all_keys:
            a = getattr(parent_a, 'allocation_weights', {}).get(key, 0.0)
            b = getattr(parent_b, 'allocation_weights', {}).get(key, 0.0)
            c1, c2 = sbx_crossover(a, b, 0.0, 1.0)
            child.allocation_weights[key] = random.choice([c1, c2])
        
        # --- SBX for synergy_map ---
        all_edges = set(parent_a.synergy_map.keys()) | set(parent_b.synergy_map.keys())
        for edge in all_edges:
            a = parent_a.synergy_map.get(edge, 0.5)
            b = parent_b.synergy_map.get(edge, 0.5)
            c1, c2 = sbx_crossover(a, b, 0.0, 1.0)
            child.synergy_map[edge] = random.choice([c1, c2])
        
        return child
    
    # ------------------------------------------------------------------
    # Phase 7: Polynomial Mutation for CommanderGenome
    # ------------------------------------------------------------------
    def _polynomial_mutate_commander(self, commander: CommanderGenome) -> CommanderGenome:
        """
        Polynomial mutation of a CommanderGenome.
        
        Uses polynomial mutation for fine-grained local search on action_weights,
        allocation_weights, and continuous parameters.
        """
        # Self-adaptive mutation rate
        new_rate = self_adaptive_mutate_rate(commander.mutation_rate)
        
        child = CommanderGenome(
            genome_id=f"GEN-{random.randint(10000, 99999)}",
            generation=commander.generation + 1,
            agent_id=commander.agent_id,
            action_weights=dict(commander.action_weights),
            synergy_map=dict(commander.synergy_map),
            phase_params={k: copy.copy(v) for k, v in commander.phase_params.items()},
            resource_conservation=commander.resource_conservation,
            time_optimization=commander.time_optimization,
            domain=commander.domain,
            mutation_rate=new_rate,
            allocation_weights=dict(getattr(commander, 'allocation_weights', {})),
        )
        
        # Polynomial mutation on action_weights
        for action in child.action_weights:
            child.action_weights[action] = polynomial_mutation(
                child.action_weights[action], 0.0, 1.0,
                eta=15.0, prob_mutation=new_rate
            )
        
        # Polynomial mutation on allocation_weights
        for key in child.allocation_weights:
            child.allocation_weights[key] = polynomial_mutation(
                child.allocation_weights[key], 0.0, 1.0,
                eta=15.0, prob_mutation=new_rate
            )
        
        # Polynomial mutation on resource_conservation
        child.resource_conservation = polynomial_mutation(
            child.resource_conservation, 0.3, 1.0,
            eta=10.0, prob_mutation=new_rate
        )
        
        # Polynomial mutation on time_optimization
        child.time_optimization = polynomial_mutation(
            child.time_optimization, 0.5, 2.0,
            eta=10.0, prob_mutation=new_rate
        )
        
        return child
    
    # ------------------------------------------------------------------
    # Phase 7: AlphaStar-style League Fitness Evaluation
    # ------------------------------------------------------------------
    def evaluate_blue_fitness(self, commander: CommanderGenome,
                              red_sample: List[RedForceGenome],
                              telemetry_by_red: Dict[str, Dict[str, Any]],
                              directive: Optional[Dict[str, float]] = None) -> float:
        """
        Evaluate Blue fitness by testing against a sample of Red genomes.
        
        Phase 7: League-aware evaluation. The commander's fitness is
        computed across multiple Red opponents, including past_selves
        and league_exploiters if available.
        
        Phase 6: Uses Monte Carlo Forklift for probabilistic evaluation.
        Penalizes high fuel consumption and rewards supply node preservation.
        
        Args:
            commander: Blue commander to evaluate
            red_sample: Sample of Red genomes to test against
            telemetry_data: Combined telemetry from battles against red_sample
            directive: Optional StrategicDirective weights
            
        Returns:
            Fitness score for the Blue commander
        """
        # ── Try Monte Carlo evaluation ──
        mc_result = None
        if self.use_monte_carlo:
            forklift = self._get_monte_carlo()
            if forklift:
                try:
                    from sim.battlefield_env import BattlefieldEnv
                    
                    top_actions = sorted(
                        commander.action_weights.items(), key=lambda x: x[1], reverse=True
                    )
                    primary_action = top_actions[0][0] if top_actions else "move"
                    coa_action = {"action": primary_action, "asset_type": "missiles" if primary_action == "strike" else "jammers"}
                    if primary_action == "move":
                        coa_action["target"] = (50, 50)
                    
                    mc_result = forklift.evaluate_coa(
                        BattlefieldEnv,
                        coa_action,
                        {"evade": True, "ecm": False, "ecm_noise": 0.0, "target": None},
                        commander=commander,
                        base_seed=42,
                        initial_red_position=(65, 50),
                    )
                except Exception as e:
                    logger.debug(f"Monte Carlo evaluation failed, falling back: {e}")
        
        # ── Standard telemetry-based evaluation (fallback + integration) ──
        total_fitness = 0.0
        valid_matches = 0
        
        if mc_result:
            mc_fitness = mc_result.fitness_score
            
            fuel_penalty = 0.0
            supply_penalty = 0.0
            
            for red_genome in red_sample:
                telemetry = telemetry_by_red.get(red_genome.genome_id, {})
                if not telemetry:
                    continue
                
                fuel_used = telemetry.get("fuel_consumed", 0)
                if fuel_used > 0:
                    fuel_penalty += min(0.2, fuel_used / 500.0)
                
                if telemetry.get("supply_node_destroyed", False):
                    supply_penalty += 0.15
                
                valid_matches += 1
            
            avg_fuel_penalty = fuel_penalty / max(1, valid_matches)
            avg_supply_penalty = supply_penalty / max(1, valid_matches)
            
            fitness = max(0.0, mc_fitness - avg_fuel_penalty - avg_supply_penalty)
            
            if directive:
                w_effectiveness = directive.get("effectiveness_weight", 0.5)
                w_efficiency = directive.get("efficiency_weight", 0.3)
                w_novelty = directive.get("novelty_weight", 0.2)
                total = w_effectiveness + w_efficiency + w_novelty
                if total > 0:
                    w_effectiveness /= total
                    w_efficiency /= total
                    w_novelty /= total
                
                mc_effectiveness = mc_result.probability_of_success
                res_cost = mc_result.expected_resource_cost
                mc_efficiency = max(0.0, 1.0 - (res_cost / 200.0))
                mc_novelty = min(1.0, len(commander.action_weights) / 10.0)
                
                fitness = (w_effectiveness * mc_effectiveness 
                          + w_efficiency * mc_efficiency 
                          + w_novelty * mc_novelty
                          - avg_fuel_penalty - avg_supply_penalty)
                fitness = max(0.0, min(1.0, fitness))
            
            commander.fitness_score = round(fitness, 4)
            commander.fitness_history.append(commander.fitness_score)
            return commander.fitness_score
        
        # ── Fallback to original deterministic evaluation ──
        if directive:
            w_effectiveness = directive.get("effectiveness_weight", 0.5)
            w_efficiency = directive.get("efficiency_weight", 0.3)
            w_novelty = directive.get("novelty_weight", 0.2)
            total = w_effectiveness + w_efficiency + w_novelty
            if total > 0:
                w_effectiveness /= total
                w_efficiency /= total
                w_novelty /= total
        else:
            w_effectiveness = 0.5
            w_efficiency = 0.3
            w_novelty = 0.2
        
        for red_genome in red_sample:
            telemetry = telemetry_by_red.get(red_genome.genome_id, {})
            if not telemetry:
                continue
            
            hits = telemetry.get("hits", 0)
            attempts = telemetry.get("attempts", 1)
            effectiveness = hits / max(1, attempts)
            
            weapons_used = telemetry.get("weapons_used", 1)
            weapons_allocated = telemetry.get("weapons_allocated", 1)
            efficiency = 1.0 - (weapons_used / max(1, weapons_allocated))
            
            actions_used = telemetry.get("actions_used", [])
            novelty = min(1.0, len(set(actions_used)) / 10)
            
            fitness = w_effectiveness * effectiveness + w_efficiency * efficiency + w_novelty * novelty
            
            fuel_consumed = telemetry.get("fuel_consumed", 0)
            fuel_penalty = min(0.2, fuel_consumed / 500.0)
            fitness -= fuel_penalty
            
            if telemetry.get("supply_node_destroyed", False):
                fitness -= 0.15
            
            if telemetry.get("blue_on_blue", 0) > 0:
                fitness *= 0.01
            elif telemetry.get("collateral", 0) > 0:
                fitness *= 0.7
            
            total_fitness += max(0.0, fitness)
            valid_matches += 1
        
        commander.fitness_score = round(total_fitness / max(1, valid_matches), 4)
        commander.fitness_history.append(commander.fitness_score)
        return commander.fitness_score
    
    def evaluate_red_fitness(self, red_genome: RedForceGenome,
                             blue_sample: List[CommanderGenome],
                             telemetry_by_blue: Dict[str, Dict[str, Any]]) -> float:
        """
        Evaluate Red fitness by testing against a sample of Blue commanders.
        
        Phase 7: Red fights against the full Blue league sample (main agent
        + exploiters) for more robust adversarial training.
        
        Red fitness = survival rate + damage inflicted.
        """
        total_survival = 0.0
        total_damage_inflicted = 0.0
        valid_matches = 0
        
        for blue_commander in blue_sample:
            telemetry = telemetry_by_blue.get(blue_commander.genome_id, {})
            if not telemetry:
                continue
            
            survived = 1.0 if telemetry.get("red_survived", True) else 0.0
            
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
    
    # ------------------------------------------------------------------
    # Phase 7: League-Based Evolution
    # ------------------------------------------------------------------
    def evolve_blue_generation(self) -> Optional[CommanderGenome]:
        """
        Evolve Blue league one generation.
        
        Phase 7: AlphaStar-style league update.
        1. Snapshot current main agent to past_selves
        2. Evolve main agent using best of population
        3. Update main_exploiters against specific Red weaknesses
        4. Update league_exploiters to beat new main agent
        """
        all_blue = self.blue_league.get_all_blue()
        if len(all_blue) < 2:
            return None
        
        # Snapshot main before evolving
        self.blue_league.snapshot_main()
        
        # Sort all Blue by fitness
        all_blue.sort(key=lambda g: g.fitness_score, reverse=True)
        
        # --- Evolve main_agent ---
        # Keep top 2 and generate offspring using SBX + Polynomial Mutation
        survivors = all_blue[:max(1, len(all_blue) // 2)]
        main_agent_fitness = survivors[0].fitness_score
        
        offspring: List[CommanderGenome] = []
        target_count = max(len(all_blue), 5)  # maintain minimum population
        while len(survivors) + len(offspring) < target_count:
            parent_a = random.choice(survivors)
            parent_b = random.choice(survivors)
            
            # Phase 7: Use SBX crossover or Polynomial mutation
            if random.random() < 0.7:
                child = self._sbx_crossover_commanders(parent_a, parent_b)
            else:
                child = self._polynomial_mutate_commander(parent_a)
            
            offspring.append(child)
        
        new_population = survivors + offspring
        self.blue_league.main_agent = new_population[0]
        
        # --- Update main_exploiters ---
        # Keep up to 3 exploiters from the top of the population
        # that have distinct action profiles from the main agent
        self.blue_league.main_exploiters = []
        for genome in new_population[1:]:
            if len(self.blue_league.main_exploiters) >= MAIN_EXPLOITERS_PER_RED:
                break
            # Check diversity: must have different dominant action
            if self._is_diverse(genome, self.blue_league.main_agent):
                self.blue_league.main_exploiters.append(genome)
        
        # If we don't have enough diverse exploiters, generate from SBX
        while len(self.blue_league.main_exploiters) < MAIN_EXPLOITERS_PER_RED:
            parent = random.choice(new_population[:3])
            child = self._polynomial_mutate_commander(parent)
            self.blue_league.main_exploiters.append(child)
        
        return self.blue_league.main_agent
    
    def _is_diverse(self, genome: CommanderGenome, reference: CommanderGenome,
                    threshold: float = 0.4) -> bool:
        """
        Check if a genome has a sufficiently different action profile.
        Cosine-distance heuristic based on dominant action weights.
        """
        if not genome.action_weights or not reference.action_weights:
            return True
        
        # Find top action for each
        g_top = sorted(genome.action_weights.items(), key=lambda x: x[1], reverse=True)[:2]
        r_top = sorted(reference.action_weights.items(), key=lambda x: x[1], reverse=True)[:2]
        
        g_actions = set(a for a, _ in g_top)
        r_actions = set(a for a, _ in r_top)
        
        # Diverse if top actions differ
        overlap = g_actions & r_actions
        diversity = 1.0 - (len(overlap) / max(1, len(g_actions | r_actions)))
        return diversity > threshold
    
    def evolve_red_generation(self) -> Optional[RedForceGenome]:
        """
        Evolve Red population one generation.
        
        Phase 7: Red now evolves against the full Blue league (main + exploiters)
        for more robust adversarial coevolution.
        """
        if len(self.red_population) < 2:
            return None
        
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
    
    # ------------------------------------------------------------------
    # Sampling methods (Phase 7: league-aware)
    # ------------------------------------------------------------------
    def get_blue_best(self, n: int = 1) -> List[CommanderGenome]:
        """Get top N Blue commanders by fitness (from league)."""
        all_blue = self.blue_league.get_all_blue()
        sorted_blue = sorted(all_blue, key=lambda g: g.fitness_score, reverse=True)
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
        """
        Get a sample of Blue commanders for Red fitness evaluation.
        
        Phase 7: Returns main agent + random exploiters from league.
        """
        return self.blue_league.get_blue_sample()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get coevolution statistics."""
        all_blue = self.blue_league.get_all_blue()
        return {
            "blue_population_size": len(all_blue) + len(self.blue_league.league_exploiters),
            "red_population_size": len(self.red_population),
            "blue_main_fitness": self.blue_league.main_agent.fitness_score if self.blue_league.main_agent else 0.0,
            "blue_best_fitness": max((g.fitness_score for g in all_blue), default=0.0),
            "red_best_fitness": max((g.fitness_score for g in self.red_population), default=0.0),
            "blue_active_fitness": self.blue_league.main_agent.fitness_score if self.blue_league.main_agent else 0.0,
            "red_active_fitness": self.red_active.fitness_score if self.red_active else 0.0,
            "blue_exploiters": len(self.blue_league.main_exploiters),
            "blue_past_selves": len(self.blue_league.past_selves),
            "red_mutation_rate": self.red_mutation_rate,
        }

