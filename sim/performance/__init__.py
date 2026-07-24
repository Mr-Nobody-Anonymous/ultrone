"""Performance and scaling module for large-scale simulation.

Provides infrastructure for distributed and accelerated simulation:

- ``ParallelEngine``: Multi-threaded parallel simulation
- ``DistributedSimulator``: Distributed simulation across nodes
- ``RayIntegration``: Ray-based distributed computing
- ``GPUAccelerator``: GPU-accelerated computation
- ``Profiler``: Performance profiling and benchmarking
"""

from .parallel_engine import ParallelEngine, ParallelConfig
from .distributed_sim import DistributedSimulator, DistributedConfig
from .ray_integration import RayIntegration, RayConfig
from .gpu_accelerator import GPUAccelerator, GPUConfig
from .profiler import Profiler, ProfilerConfig

__all__ = [
    "ParallelEngine", "ParallelConfig",
    "DistributedSimulator", "DistributedConfig",
    "RayIntegration", "RayConfig",
    "GPUAccelerator", "GPUConfig",
    "Profiler", "ProfilerConfig",
]
