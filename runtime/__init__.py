"""Central runtime helpers for hardware-aware execution."""

from .device import DeviceType, HardwareProfile, detect_hardware_profile
from .precision import PrecisionMode, PrecisionPolicy, select_precision
from .compilation import CompilationManager, compile_model
from .batching import batch_inference, recommended_batch_size
from .inference import ModelCache, ModelRuntime, Runtime, RuntimeConfig, benchmark_hardware

__all__ = [
    "DeviceType",
    "HardwareProfile",
    "detect_hardware_profile",
    "PrecisionMode",
    "PrecisionPolicy",
    "select_precision",
    "CompilationManager",
    "compile_model",
    "batch_inference",
    "recommended_batch_size",
    "ModelCache",
    "ModelRuntime",
    "Runtime",
    "RuntimeConfig",
    "benchmark_hardware",
]
