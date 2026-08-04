"""Hardware — Backend abstractions for ROCm, Metal, TPU, XPU, Vulkan."""
from .backend import HardwareBackend, BackendRegistry
__all__ = ["HardwareBackend", "BackendRegistry"]
