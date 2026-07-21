# Copyright (c) Ultrone Contributors. All rights reserved.
"""
Evolution Lab
=============
The central orchestrator for all self-evolution activities.
Extended with military fitness functions.
"""

import logging
import random
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from datetime import datetime

from .genome import (
    Genome,
    GenomeEngine,
    MutationStrategy,
    CrossoverStrategy,
    SelectionStrategy,
)
from .performance_telemetry import PerformanceTelemetry, TelemetryMetrics

logger = logging.getLogger("Ultrone.Brain.Learning.Lab")


@dataclass
class EvolutionConfig:
    """Configuration for the evolution lab."""
    enabled: bool = True
    auto_evolve: bool = True
    evolution_interval_actions: int = 10  # Trigger evolution every N actions
    min_fitness_threshold: float = 0.75
    population_size: int = 10
    mutation_strategy: str = "adaptive"
    crossover_strategy: str = "blend"
    selection_strategy: str = "tournament"
    max_generations: int = 100
    preserve_best_genome: bool = True
    telemetry_window_size: int = 100
    
    def to_dict(self) -> dict:
        return {
            "enabled": self.enabled,
            "auto_evolve": self.auto_evolve,
            "evolution_interval_actions": self.evolution_interval_actions,
            "min_fitness_threshold": self.min_fitness_threshold,
            "population_size": self.population_size,
            "mutation_strategy": self.mutation_strategy,
            "crossover_strategy": self.crossover_strategy,
            "selection_strategy": self.selection_strategy,
            "max_generations": self.max_generations,
            "preserve_best_genome": self.preserve_best_genome,
            "telemetry_window_size": self.telemetry_window_size,
        }


class EvolutionLab:
    """
    Central evolution orchestrator.
    
    Manages the complete evolution lifecycle:
    1. Monitor performance via telemetry
    2. Trigger evolution when fitness drops
    3. Run genome mutation/crossover cycles
    4. Validate new genomes in sandbox
    5. Deploy improved genomes
    6. Track evolution history
    
    Extended with military kill chain fitness functions.
    """
    
    def __init__(
        self,
        config: Optional[EvolutionConfig] = None,
        genome_engine: Optional[GenomeEngine] = None,
        telemetry: Optional[PerformanceTelemetry] = None,
    ):
        self.config = config or EvolutionConfig()
        self.telemetry = telemetry or PerformanceTelemetry(
            window_size=self.config.telemetry_window_size,
        )
        
        # Map strategy strings to enums
        strategy_map = {
            "uniform": MutationStrategy.UNIFORM,
            "gaussian": MutationStrategy.GAUSSIAN,
            "adaptive": MutationStrategy.ADAPTIVE,
            "swap": MutationStrategy.SWAP,
            "reset": MutationStrategy.RESET,
        }
        crossover_map = {
            "single_point": CrossoverStrategy.SINGLE_POINT,
            "two_point": CrossoverStrategy.TWO_POINT,
            "uniform": CrossoverStrategy.UNIFORM,
            "blend": CrossoverStrategy.BLEND,
        }
        selection_map = {
            "tournament": SelectionStrategy.TOURNAMENT,
            "roulette_wheel": SelectionStrategy.ROULETTE_WHEEL,
            "rank_based": SelectionStrategy.RANK_BASED,
            "elitist": SelectionStrategy.ELITIST,
        }
        
        self.genome_engine = genome_engine or GenomeEngine(
            mutation_strategy=strategy_map.get(
                self.config.mutation_strategy, MutationStrategy.ADAPTIVE
            ),
            crossover_strategy=crossover_map.get(
                self.config.crossover_strategy, CrossoverStrategy.BLEND
            ),
            selection_strategy=selection_map.get(
                self.config.selection_strategy, SelectionStrategy.TOURNAMENT
            ),
            population_size=self.config.population_size,
            min_acceptable_fitness=self.config.min_fitness_threshold,
        )
        
        self.action_count = 0
        self.evolution_count = 0
        self.evolution_history: List[Dict[str, Any]] = []
        self._initialized = False
    
    def initialize(self, agent_id: str = "ultrone-agent") -> None:
        """Initialize with a default genome if none exists."""
        if not self.genome_engine.active_genome:
            self.genome_engine.create_default_genome(agent_id)
            logger.info(
                "Evolution Lab initialized: Agent=%s, Capsules=%d, Genes=%d",
                agent_id,
                len(self.genome_engine.active_genome.capsules),
                len(self.genome_engine.active_genome.get_all_genes()),
            )
        self._initialized = True
    
    def log_action(
        self,
        action: str,
        domain: str,
        success: bool,
        response_time_ms: float,
        agent_id: str = "",
        error_type: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        kill_chain_phase: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Log an action through telemetry and check if evolution is needed.
        
        This is the main integration point — call this after every agent action.
        Extended with kill chain phase tracking for military fitness.
        """
        if not self.config.enabled:
            return {"evolved": False, "reason": "evolution_disabled"}
        
        if not self._initialized:
            self.initialize(agent_id)
        
        generation = self.genome_engine.generation if self.genome_engine.active_genome else 0
        
        # Build context with kill chain info
        full_context = context or {}
        if kill_chain_phase:
            full_context["kill_chain_phase"] = kill_chain_phase
        
        result = self.telemetry.log_action(
            action=action,
            domain=domain,
            success=success,
            response_time_ms=response_time_ms,
            agent_id=agent_id,
            genome_generation=generation,
            error_type=error_type,
            context=full_context,
        )
        
        # Feed fitness to genome engine
        if self.genome_engine.active_genome:
            self.genome_engine.record_fitness(result["fitness"])
        
        self.action_count += 1
        
        # Check if we should run an evolution cycle
        evolved = False
        if self.config.auto_evolve and self.action_count % self.config.evolution_interval_actions == 0:
            evolved = self.run_evolution_cycle()
        
        return {
            "evolved": evolved,
            "fitness": result["fitness"],
            "action_count": self.action_count,
            "generation": generation,
        }
    
    def run_evolution_cycle(self) -> bool:
        """
        Run one evolution cycle.
        
        Returns True if a new genome was deployed.
        """
        if not self.config.enabled:
            return False
        
        # Get failure analysis to guide evolution
        failure_analysis = self.telemetry.get_failure_analysis()
        
        # Run genome evolution
        new_genome = self.genome_engine.evolve()
        
        if new_genome:
            self.evolution_count += 1
            self.evolution_history.append({
                "timestamp": datetime.utcnow().isoformat(),
                "generation": new_genome.generation,
                "fitness_score": new_genome.fitness_score,
                "capsules": len(new_genome.capsules),
                "genes": len(new_genome.get_all_genes()),
                "failure_analysis": failure_analysis,
            })
            
            logger.info(
                "🧬 Evolution Cycle %d complete: Generation %d deployed (fitness=%.3f)",
                self.evolution_count, new_genome.generation, new_genome.fitness_score,
            )
            return True
        
        return False
    
    def get_genome_parameters(self) -> Dict[str, float]:
        """Get current genome parameters as a flat dict for controller use."""
        if not self.genome_engine.active_genome:
            return {}
        
        params = {}
        for gene in self.genome_engine.active_genome.get_all_genes():
            params[gene.name] = gene.value
        return params
    
    def get_stats(self) -> Dict[str, Any]:
        """Get comprehensive evolution lab statistics."""
        return {
            "config": self.config.to_dict(),
            "genome_engine": self.genome_engine.get_stats(),
            "telemetry": self.telemetry.get_stats(),
            "lab": {
                "initialized": self._initialized,
                "action_count": self.action_count,
                "evolution_count": self.evolution_count,
                "last_evolution": self.evolution_history[-1] if self.evolution_history else None,
            },
        }
    
    def get_evolution_summary(self) -> str:
        """Get a human-readable summary of evolution status."""
        stats = self.get_stats()
        lines = [
            "=" * 60,
            "🧬 ULTRONE EVOLUTION LAB STATUS",
            "=" * 60,
            f"Status: {'ACTIVE' if self.config.enabled else 'DISABLED'}",
            f"Generation: {stats['genome_engine']['generation']}",
            f"Evolution Cycles: {stats['lab']['evolution_count']}",
            f"Actions Tracked: {stats['lab']['action_count']}",
            f"Best Fitness: {stats['genome_engine']['best_fitness']:.3f}",
            f"Population Size: {stats['genome_engine']['population_size']}",
            "",
            "Active Capsules:",
        ]
        
        if self.genome_engine.active_genome:
            for name, capsule in self.genome_engine.active_genome.capsules.items():
                genes_str = ", ".join(f"{g.name}={g.value:.3f}" for g in capsule.genes)
                lines.append(f"  ├─ {name}: [{genes_str}]")
        
        telemetry = stats.get("telemetry", {})
        metrics = telemetry.get("metrics", {})
        if metrics:
            lines.extend([
                "",
                f"Success Rate: {metrics.get('success_rate', 0):.1%}",
                f"Avg Response: {metrics.get('avg_response_time_ms', 0):.0f}ms",
                f"Kill Chain Success: {metrics.get('kill_chain_success_rate', 0):.1%}",
                f"Collateral Rate: {metrics.get('collateral_rate', 0):.2%}",
                f"Total Events: {metrics.get('total_actions', 0)}",
            ])
        
        lines.append("=" * 60)
        return "\n".join(lines)