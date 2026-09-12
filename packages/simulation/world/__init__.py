"""Simulation world state and environment management."""
try:
    from simulation.world import SimulationWorld
except ImportError:
    SimulationWorld = None

__all__ = ["SimulationWorld"]
