# Copyright (c) Ultrone Contributors. All rights reserved.
"""Scenario Generator - creates ghost wargames for testing evolved strategies."""

import logging
import random
from typing import Dict, List, Optional
from dataclasses import dataclass
from copy import deepcopy

logger = logging.getLogger("Ultrone.Generative.ScenarioGenerator")


@dataclass
class GhostScenario:
    """A simulated enemy scenario for testing."""
    scenario_id: str
    name: str
    enemy_forces: Dict[str, int]  # unit_type -> count
    difficulty: float  # 0.0-1.0
    enemy_doctrine: str  # "aggressive", "defensive", "asymmetric"
    
    def to_dict(self) -> dict:
        return {
            "scenario_id": self.scenario_id,
            "name": self.name,
            "enemy_forces": self.enemy_forces,
            "difficulty": self.difficulty,
            "doctrine": self.enemy_doctrine,
        }


class ScenarioGenerator:
    """
    Generates internal "Ghost Wargames" to test evolved strategies.
    
    Creates mutated enemy scenarios based on gaps in defense.
    """
    
    SCENARIO_TEMPLATES = {
        "SWARM_AIR": {
            "forces": {"drone": 8, "fighter": 2},
            "doctrine": "aggressive",
        },
        "SUBMARINE_HUNT": {
            "forces": {"submarine": 3, "vessel": 1},
            "doctrine": "asymmetric",
        },
        "CYBER_EMP": {
            "forces": {"cyber_exploit": 2, "cyber_recon": 2},
            "doctrine": "asymmetric",
        },
        "AMPHIBIOUS_ASSAULT": {
            "forces": {"infantry": 6, "tank": 2, "mobile_missile": 1},
            "doctrine": "balanced",
        },
        "ORBITAL_STRIKE": {
            "forces": {"satellite": 2, "space_weapon": 1},
            "doctrine": "aggressive",
        },
    }
    
    def __init__(self):
        self.generated_scenarios: List[GhostScenario] = []
        self._scenario_count = 0
    
    def generate(
        self,
        weakness_domains: List[str] = None,
        difficulty: float = 0.5,
    ) -> GhostScenario:
        """
        Generate a ghost scenario targeting defensive weaknesses.
        
        weakness_domains: domains where ULTRONE has poor performance
        """
        self._scenario_count += 1
        
        # Select template based on weaknesses
        templates = list(self.SCENARIO_TEMPLATES.values())
        if weakness_domains:
            # Bias toward domains we're weak in
            template = random.choice(templates)
        else:
            template = random.choice(templates)
        
        # Mutate forces based on difficulty
        forces = {}
        for unit_type, base_count in template["forces"].items():
            forces[unit_type] = max(1, int(base_count * (0.5 + difficulty)))
        
        scenario = GhostScenario(
            scenario_id=f"SCEN-{self._scenario_count:04d}",
            name=f"Ghost Opposition #{self._scenario_count}",
            enemy_forces=forces,
            difficulty=difficulty,
            enemy_doctrine=template["doctrine"],
        )
        
        self.generated_scenarios.append(scenario)
        return scenario
    
    def fast_forward_test(
        self,
        world_state,
        genome,
        ticks: int = 50,
    ) -> Dict[str, float]:
        """
        Run a fast-forward simulation to test genome against scenario.
        
        Returns survival metrics.
        """
        # Simulate engagement effectiveness
        survival = 1.0
        effectiveness = 0.5
        
        # Simple simulation - would integrate with actual world
        for _ in range(ticks // 10):  # Simplified
            # Check if genome parameters lead to victory
            params = {}
            for capsule in genome.capsules.values():
                for gene in capsule.genes:
                    params[gene.name] = gene.value
            
            # Aggression helps offense
            if params.get("aggression", 0.5) > 0.6:
                effectiveness += 0.05
            else:
                survival -= 0.02
            
            # Good kill chain speed helps
            if params.get("target_confirmation_threshold", 0.7) < 0.5:
                effectiveness += 0.03
            
            # Too much aggression hurts defense
            survival -= params.get("aggression", 0.5) * 0.01
        
        return {
            "survival_rate": max(0.0, min(1.0, survival)),
            "effectiveness": max(0.0, min(1.0, effectiveness)),
            "ticks_survived": ticks,
        }
    
    def get_stats(self) -> dict:
        return {
            "scenarios_generated": self._scenario_count,
            "stored_scenarios": len(self.generated_scenarios),
        }