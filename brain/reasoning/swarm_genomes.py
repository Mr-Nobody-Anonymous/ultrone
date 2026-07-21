# Copyright (c) Ultrone Contributors. All rights reserved.
"""Swarm genome architecture for ULTRONE Phase 1."""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

# Reuse existing evolutionary base types for compatibility
from .evolutionary_coagen import EvolutionaryGenome, PhaseParameters, violates_roe


@dataclass
class AssetMicroGenome:
    """
    Local genome controlling an individual asset's behavior.
    
    Contains fine-grained parameters like heading, timing, and aggression.
    """
    asset_type: str  # "drone", "jammer", "missile"
    asset_id: str
    heading: float = 0.0
    timing: float = 0.0
    aggressiveness: float = 0.5
    formation_spread: float = 10.0
    adaptation_rate: float = 0.1

    def mutate(self, mutation_rate: float = 0.15) -> AssetMicroGenome:
        """Create mutated copy of this micro genome."""
        child = AssetMicroGenome(
            asset_type=self.asset_type,
            asset_id=self.asset_id,
            heading=self.heading,
            timing=self.timing,
            aggressiveness=self.aggressiveness,
            formation_spread=self.formation_spread,
            adaptation_rate=self.adaptation_rate,
        )
        if random.random() < mutation_rate:
            child.heading = (child.heading + random.gauss(0, 30)) % 360
        if random.random() < mutation_rate:
            child.timing = max(0.0, min(1.0, child.timing + random.gauss(0, 0.1)))
        if random.random() < mutation_rate:
            child.aggressiveness = max(0.0, min(1.0, child.aggressiveness + random.gauss(0, 0.1)))
        if random.random() < mutation_rate:
            child.formation_spread = max(1.0, min(50.0, child.formation_spread + random.gauss(0, 5)))
        if random.random() < mutation_rate:
            child.adaptation_rate = max(0.01, min(0.5, child.adaptation_rate + random.gauss(0, 0.05)))
        return child

    def to_dict(self) -> Dict[str, Any]:
        return {
            "asset_type": self.asset_type,
            "asset_id": self.asset_id,
            "heading": self.heading,
            "timing": self.timing,
            "aggressiveness": self.aggressiveness,
            "formation_spread": self.formation_spread,
            "adaptation_rate": self.adaptation_rate,
        }


@dataclass
class CommanderGenome(EvolutionaryGenome):
    """
    High-level genome dictating overall strategy and asset allocation.
    
    Inherits all tactical parameters from EvolutionaryGenome and adds
    allocation weights that determine how the fleet is composed.
    """
    allocation_weights: Dict[str, float] = field(default_factory=lambda: {
        "drones_recon": 0.5,
        "drones_strike": 0.2,
        "jammers_ew": 0.3,
        "missiles_reserve": 0.3,
        "missiles_engage": 0.4,
    })

    def spawn_asset_micro_genomes(self) -> List[AssetMicroGenome]:
        """Spawn a fleet of micro genomes based on allocation rules."""
        fleet: List[AssetMicroGenome] = []
        num_drones = 2
        num_jammers = 1
        num_missiles = 2

        for i in range(num_drones):
            fleet.append(AssetMicroGenome(
                asset_type="drone",
                asset_id=f"drone-{i}",
                heading=random.uniform(0, 360),
                timing=random.uniform(0, 1),
                aggressiveness=self.allocation_weights.get("drones_strike", 0.2),
                formation_spread=random.uniform(5, 20),
                adaptation_rate=random.uniform(0.05, 0.2),
            ))

        for i in range(num_jammers):
            fleet.append(AssetMicroGenome(
                asset_type="jammer",
                asset_id=f"jammer-{i}",
                heading=random.uniform(0, 360),
                timing=random.uniform(0, 1),
                aggressiveness=self.allocation_weights.get("jammers_ew", 0.3),
                formation_spread=random.uniform(3, 10),
                adaptation_rate=random.uniform(0.05, 0.2),
            ))

        for i in range(num_missiles):
            fleet.append(AssetMicroGenome(
                asset_type="missile",
                asset_id=f"missile-{i}",
                heading=random.uniform(0, 360),
                timing=random.uniform(0, 1),
                aggressiveness=self.allocation_weights.get("missiles_engage", 0.4),
                formation_spread=random.uniform(2, 8),
                adaptation_rate=random.uniform(0.05, 0.2),
            ))

        return fleet

    def to_dict(self) -> Dict[str, Any]:
        base = super().to_dict()
        base["allocation_weights"] = self.allocation_weights
        return base