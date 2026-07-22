# Copyright (c) Ultrone Contributors. All rights reserved.
"""Red Force adversarial genome architecture for ULTRONE Phase 2."""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class RedForceGenome:
    """
    Adversarial genome for Red Force tactics.
    
    Focuses on evasion, ECM, and formation density rather than kill chains.
    """
    genome_id: str
    generation: int = 0
    agent_id: str = "red-force"
    
    # Evasion parameters
    evasion_tendency: float = 0.5  # 0-1: higher = more likely to change heading
    burst_speed_factor: float = 1.0  # multiplier for speed bursts
    heading_change_angle: float = 45.0  # max degrees to turn per step
    
    # Electronic Counter-Measures
    ecm_probability: float = 0.2  # 0-1: chance to trigger ECM each step
    ecm_noise_level: float = 0.3  # 0-1: strength of sensor degradation
    
    # Formation/swarm density
    formation_density: float = 0.5  # 0=loose, 1=tight stacking
    dispersion_radius: float = 20.0  # grid units of spread
    
    # Evolution control
    mutation_rate: float = 0.15
    fitness_score: float = 0.0
    fitness_history: List[float] = field(default_factory=list)
    
    def mutate(self, mutation_rate: Optional[float] = None) -> RedForceGenome:
        """Create mutated copy of this genome."""
        if mutation_rate is None:
            mutation_rate = self.mutation_rate
            
        child = RedForceGenome(
            genome_id=f"RED-{random.randint(10000, 99999)}",
            generation=self.generation + 1,
            agent_id=self.agent_id,
            evasion_tendency=self.evasion_tendency,
            burst_speed_factor=self.burst_speed_factor,
            heading_change_angle=self.heading_change_angle,
            ecm_probability=self.ecm_probability,
            ecm_noise_level=self.ecm_noise_level,
            formation_density=self.formation_density,
            dispersion_radius=self.dispersion_radius,
            mutation_rate=self.mutation_rate,
        )
        
        # Mutate evasion parameters
        if random.random() < mutation_rate:
            child.evasion_tendency = max(0.0, min(1.0,
                child.evasion_tendency + random.gauss(0, 0.1)))
        if random.random() < mutation_rate:
            child.burst_speed_factor = max(1.0, min(5.0,
                child.burst_speed_factor + random.gauss(0, 0.3)))
        if random.random() < mutation_rate:
            child.heading_change_angle = max(10.0, min(180.0,
                child.heading_change_angle + random.gauss(0, 15)))
        
        # Mutate ECM parameters
        if random.random() < mutation_rate:
            child.ecm_probability = max(0.0, min(1.0,
                child.ecm_probability + random.gauss(0, 0.1)))
        if random.random() < mutation_rate:
            child.ecm_noise_level = max(0.0, min(1.0,
                child.ecm_noise_level + random.gauss(0, 0.1)))
        
        # Mutate formation parameters
        if random.random() < mutation_rate:
            child.formation_density = max(0.0, min(1.0,
                child.formation_density + random.gauss(0, 0.1)))
        if random.random() < mutation_rate:
            child.dispersion_radius = max(5.0, min(50.0,
                child.dispersion_radius + random.gauss(0, 5)))
        
        return child
    
    def crossover(self, other: RedForceGenome) -> RedForceGenome:
        """Crossover two RedForceGenomes."""
        child = RedForceGenome(
            genome_id=f"RED-{random.randint(10000, 99999)}",
            generation=max(self.generation, other.generation) + 1,
            agent_id=self.agent_id,
            mutation_rate=random.uniform(0.1, 0.2),
            evasion_tendency=random.uniform(self.evasion_tendency, other.evasion_tendency),
            burst_speed_factor=random.uniform(self.burst_speed_factor, other.burst_speed_factor),
            heading_change_angle=random.uniform(self.heading_change_angle, other.heading_change_angle),
            ecm_probability=random.uniform(self.ecm_probability, other.ecm_probability),
            ecm_noise_level=random.uniform(self.ecm_noise_level, other.ecm_noise_level),
            formation_density=random.uniform(self.formation_density, other.formation_density),
            dispersion_radius=random.uniform(self.dispersion_radius, other.dispersion_radius),
        )
        return child
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "genome_id": self.genome_id,
            "generation": self.generation,
            "agent_id": self.agent_id,
            "evasion_tendency": self.evasion_tendency,
            "burst_speed_factor": self.burst_speed_factor,
            "heading_change_angle": self.heading_change_angle,
            "ecm_probability": self.ecm_probability,
            "ecm_noise_level": self.ecm_noise_level,
            "formation_density": self.formation_density,
            "dispersion_radius": self.dispersion_radius,
            "mutation_rate": self.mutation_rate,
            "fitness_score": self.fitness_score,
        }
    
    def should_evade(self) -> bool:
        """Roll for evasion this turn."""
        return random.random() < self.evasion_tendency
    
    def should_trigger_ecm(self) -> bool:
        """Roll for ECM activation this turn."""
        return random.random() < self.ecm_probability
    
    def get_evasion_heading(self, current_heading: float) -> float:
        """Calculate new heading after evasion maneuver."""
        max_turn = self.heading_change_angle
        turn = random.uniform(-max_turn, max_turn)
        return (current_heading + turn) % 360
    
    def get_burst_speed(self, base_speed: int) -> int:
        """Get speed after possible burst."""
        if random.random() < 0.3:  # 30% chance of burst when evading
            return min(10, int(base_speed * self.burst_speed_factor))
        return base_speed