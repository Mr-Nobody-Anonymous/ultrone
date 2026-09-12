# Copyright (c) Ultrone Contributors. All rights reserved.
"""
Ultrone Evolution Engine
=========================
Dedicated self-evolution infrastructure inspired by:
- A-Evolve: Universal infrastructure for evolving AI agents
- evolver (GEP): Genome Evolution Protocol with gene/capsule architecture
- Agent Zero: Dynamic sub-agent creation and self-improvement
- SuperAGI: Performance telemetry and autonomous optimization
"""

from .genome import (
    Genome,
    Gene,
    Capsule,
    GenomeEngine,
    MutationStrategy,
    CrossoverStrategy,
    SelectionStrategy,
)
from .evolution_lab import EvolutionLab, EvolutionConfig
from .agent_evolver import AgentEvolver
from .performance_telemetry import PerformanceTelemetry, TelemetryMetrics

__all__ = [
    "Genome",
    "Gene",
    "Capsule",
    "GenomeEngine",
    "MutationStrategy",
    "CrossoverStrategy",
    "SelectionStrategy",
    "EvolutionLab",
    "EvolutionConfig",
    "AgentEvolver",
    "PerformanceTelemetry",
    "TelemetryMetrics",
]