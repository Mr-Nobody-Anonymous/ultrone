"""
Environment definitions for simulation.

Future: Terrain types, weather models, lighting conditions,
communication environments, electromagnetic spectrum.
"""
try:
    from simulation.environment_generator import EnvironmentGenerator
except ImportError:
    EnvironmentGenerator = None

__all__ = ["EnvironmentGenerator"]
