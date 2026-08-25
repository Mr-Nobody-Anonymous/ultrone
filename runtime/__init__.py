"""Central runtime helpers for hardware-aware execution."""

from .backend import BackendInfo, BackendManager, detect_backends
from .batching import batch_inference, recommended_batch_size
from .capabilities import Capabilities, detect_capabilities
from .compilation import CompilationManager, compile_model
from .device import DeviceType, HardwareProfile, detect_hardware_profile
from .inference import (
    InferenceScheduler,
    ModelCache,
    ModelRuntime,
    ModelState,
    Priority,
    Runtime,
    RuntimeConfig,
    benchmark_hardware,
)
from .memory import LRUCache, MemoryMonitor, ModelEvictionManager
from .policy import ChangeDetector, DecisionCache, FastSlowPolicy, PolicyConfig, ReasoningScheduler
from .precision import PrecisionMode, PrecisionPolicy, select_precision

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
    "ModelState",
    "Priority",
    "Runtime",
    "RuntimeConfig",
    "benchmark_hardware",
    "BackendInfo",
    "BackendManager",
    "detect_backends",
    "Capabilities",
    "detect_capabilities",
    "LRUCache",
    "MemoryMonitor",
    "ModelEvictionManager",
    "InferenceScheduler",
    "ChangeDetector",
    "DecisionCache",
    "FastSlowPolicy",
    "PolicyConfig",
    "ReasoningScheduler",
]
