"""Physics engine stubs for simulation."""
try:
    from simulation.physics import PhysicsEngine
except ImportError:
    PhysicsEngine = None

__all__ = ["PhysicsEngine"]
