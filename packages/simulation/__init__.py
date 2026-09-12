"""
ULTRONE Simulation Package.

Canonical location for simulation functionality. This package
re-exports from the root-level simulation/ directory for backward
compatibility, and provides sub-structure for organized access.

Sub-modules:
- world/        World state and environment
- entities/     Simulated entities
- physics/      Physics engine
- sensors/      Sensor models
- environments/ Environment definitions
- scenarios/    Scenario configurations
"""
try:
    from simulation.core import SimulationCore
    from simulation.world import SimulationWorld
    from simulation.runner import SimulationRunner
    from simulation.physics import PhysicsEngine
    from simulation.digital_twin import DigitalTwin
except ImportError:
    SimulationCore = None
    SimulationWorld = None
    SimulationRunner = None
    PhysicsEngine = None
    DigitalTwin = None

__all__ = [
    "SimulationCore",
    "SimulationWorld",
    "SimulationRunner",
    "PhysicsEngine",
    "DigitalTwin",
]
