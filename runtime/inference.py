from __future__ import annotations

"""Central model runtime — model lifecycle, caching, warmup, and inference scheduling."""

import contextlib
import logging
import threading
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Sequence, TypeVar

from .backend import BackendManager, detect_backends
from .batching import batch_inference, recommended_batch_size
from .capabilities import Capabilities, detect_capabilities
from .compilation import CompilationManager
from .device import DeviceType, HardwareProfile, detect_hardware_profile, to_device_info
from .memory import LRUCache, MemoryMonitor, ModelEvictionManager
from .precision import PrecisionMode, PrecisionPolicy, select_precision

T = TypeVar("T")

logger = logging.getLogger("Ultrone.Runtime.Inference")


class ModelState(str, Enum):
    """Model lifecycle states."""

    UNLOADED = "unloaded"
    LOADING = "loading"
    READY = "ready"
    WARM = "warm"
    ACTIVE = "active"
    IDLE = "idle"
    EVICTED = "evicted"


class Priority(str, Enum):
    """Inference request priority levels."""

    CRITICAL = "critical"
    HIGH = "high"
    NORMAL = "normal"
    LOW = "low"
    BACKGROUND = "background"


@dataclass
class RuntimeConfig:
    device: str = "auto"
    precision: str = PrecisionMode.AUTO.value
    compile: str = "auto"
    quantization: str = "auto"
    max_batch_size: int = 8
    inference_timeout: float = 30.0
    enable_model_cache: bool = True
    enable_embedding_cache: bool = True
    enable_reasoning_cache: bool = True
    enable_async_inference: bool = True
    enable_xai: bool = False
    reasoning_interval: int = 5
    performance_profile: str = "auto"  # ultra_fast, balanced, research, max_quality
    max_cached_models: int = 8
    enable_eviction: bool = True
    warmup_enabled: bool = False

    @classmethod
    def from_env(cls) -> "RuntimeConfig":
        """Create a configuration from environment variables."""
        import os

        def _env_bool(name: str, default: bool) -> bool:
            val = os.environ.get(name)
            if val is None:
                return default
            return val.lower() in {"1", "true", "yes", "on"}

        profile = os.environ.get("ULTRONE_PERFORMANCE_PROFILE", "auto").lower()
        if profile == "ultra_fast":
            return cls(
                device="auto",
                precision="auto",
                compile="auto",
                quantization="auto",
                max_batch_size=16,
                enable_model_cache=True,
                enable_embedding_cache=True,
                enable_reasoning_cache=True,
                enable_async_inference=True,
                enable_xai=False,
                reasoning_interval=10,
                performance_profile="ultra_fast",
                max_cached_models=4,
                enable_eviction=True,
                warmup_enabled=True,
            )
        if profile == "research":
            return cls(
                device="auto",
                precision="auto",
                compile="auto",
                quantization="auto",
                enable_xai=True,
                reasoning_interval=2,
                performance_profile="research",
                warmup_enabled=True,
            )
        if profile == "max_quality":
            return cls(
                device="auto",
                precision="fp32",
                compile="off",
                quantization="none",
                enable_xai=True,
                reasoning_interval=1,
                performance_profile="max_quality",
                warmup_enabled=True,
            )
        return cls(
            device=os.environ.get("ULTRONE_DEVICE", "auto"),
            precision=os.environ.get("ULTRONE_PRECISION", "auto"),
            compile=os.environ.get("ULTRONE_COMPILE", "auto"),
            quantization=os.environ.get("ULTRONE_QUANTIZATION", "auto"),
            max_batch_size=int(os.environ.get("ULTRONE_MAX_BATCH_SIZE", "8")),
            enable_model_cache=_env_bool("ULTRONE_MODEL_CACHE", True),
            enable_embedding_cache=_env_bool("ULTRONE_EMBEDDING_CACHE", True),
            enable_reasoning_cache=_env_bool("ULTRONE_REASONING_CACHE", True),
            enable_async_inference=_env_bool("ULTRONE_ASYNC_INFERENCE", True),
            enable_xai=_env_bool("ULTRONE_XAI", False),
            reasoning_interval=int(os.environ.get("ULTRONE_REASONING_INTERVAL", "5")),
            performance_profile=profile,
            max_cached_models=int(os.environ.get("ULTRONE_MAX_CACHED_MODELS", "8")),
            enable_eviction=_env_bool("ULTRONE_EVICTION", True),
            warmup_enabled=_env_bool("ULTRONE_WARMUP", False),
        )


class ModelCache:
    """Thread-safe model cache with model lifecycle tracking."""

    def __init__(self, max_size: int = 8) -> None:
        self._models: Dict[str, Any] = {}
        self._metadata: Dict[str, Dict[str, Any]] = {}
        self._access_order: List[str] = []
        self._states: Dict[str, str] = {}
        self._lock = threading.RLock()
        self.max_size = max(1, max_size)

    def get(self, model_id: str) -> Optional[Any]:
        with self._lock:
            model = self._models.get(model_id)
            if model is not None:
                self._touch(model_id)
            return model

    def put(self, model_id: str, model: Any, **metadata: Any) -> Any:
        with self._lock:
            self._models[model_id] = model
            self._metadata[model_id] = metadata
            self._touch(model_id)
            if model_id not in self._states:
                self._states[model_id] = ModelState.READY.value
            # Enforce max size
            while len(self._models) > self.max_size:
                if self._access_order:
                    victim = self._access_order[0]
                    self.remove(victim)
                else:
                    break
        return model

    def _touch(self, model_id: str) -> None:
        """Record a model access for LRU ordering."""
        if model_id in self._access_order:
            self._access_order.remove(model_id)
        self._access_order.append(model_id)

    def get_or_load(self, model_id: str, loader: Callable[[], Any], *args: Any, **kwargs: Any) -> Any:
        cached = self.get(model_id)
        if cached is not None:
            return cached
        self.set_state(model_id, ModelState.LOADING.value)
        try:
            model = loader(*args, **kwargs)
            self.put(model_id, model, **kwargs)
            self.set_state(model_id, ModelState.READY.value)
            return model
        except Exception:
            self.set_state(model_id, ModelState.UNLOADED.value)
            raise

    def remove(self, model_id: str) -> None:
        with self._lock:
            model = self._models.pop(model_id, None)
            self._metadata.pop(model_id, None)
            if model_id in self._access_order:
                self._access_order.remove(model_id)
            if model is not None and hasattr(model, "to"):
                # Best-effort CPU offload before eviction (prevents VRAM leak)
                try:
                    model.to("cpu")
                except Exception:
                    pass
            self._states[model_id] = ModelState.EVICTED.value

    def clear(self) -> None:
        with self._lock:
            for mid in list(self._models.keys()):
                self.remove(mid)
            self._states.clear()

    def set_state(self, model_id: str, state: str) -> None:
        with self._lock:
            self._states[model_id] = state

    def get_state(self, model_id: str) -> str:
        return self._states.get(model_id, ModelState.UNLOADED.value)

    def stats(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "cached_models": len(self._models),
                "keys": sorted(self._models.keys()),
                "states": dict(self._states),
                "access_order": list(self._access_order),
            }


class InferenceScheduler:
    """Lightweight inference request scheduler with priority and micro-batching."""

    def __init__(self, max_queue_size: int = 256) -> None:
        self._queue: List[Dict[str, Any]] = []
        self._lock = threading.Lock()
        self.max_queue_size = max_queue_size
        self.total_submitted = 0
        self.total_processed = 0
        self.total_cancelled = 0

    def submit(
        self,
        fn: Callable[..., T],
        *args: Any,
        priority: str = Priority.NORMAL.value,
        **kwargs: Any,
    ) -> "InferenceScheduler.SubmittedTask":
        """Submit a task to the scheduler with a priority level."""
        with self._lock:
            if len(self._queue) >= self.max_queue_size:
                raise RuntimeError(
                    f"Inference queue full ({self.max_queue_size}); request rejected (backpressure)"
                )
            task = InferenceScheduler.SubmittedTask(fn, args, kwargs)
            self._queue.append(
                {
                    "task": task,
                    "priority": priority,
                    "submitted_at": time.time(),
                }
            )
            self.total_submitted += 1
            return task

    def process_next(self) -> Optional[Any]:
        """Process the highest-priority task from the queue."""
        with self._lock:
            if not self._queue:
                return None
            # Sort by priority: CRITICAL=0, HIGH=1, NORMAL=2, LOW=3, BACKGROUND=4
            priority_order = {
                Priority.CRITICAL.value: 0,
                Priority.HIGH.value: 1,
                Priority.NORMAL.value: 2,
                Priority.LOW.value: 3,
                Priority.BACKGROUND.value: 4,
            }
            self._queue.sort(key=lambda x: priority_order.get(x["priority"], 2))
            item = self._queue.pop(0)
            self.total_processed += 1
            task = item["task"]
            try:
                return task.fn(*task.args, **task.kwargs)
            except Exception:
                logger.exception("Inference scheduler task failed")
                return None

    def cancel(self, task: "InferenceScheduler.SubmittedTask") -> bool:
        """Cancel a pending task if not yet processed."""
        with self._lock:
            for i, item in enumerate(self._queue):
                if item["task"] is task:
                    self._queue.pop(i)
                    self.total_cancelled += 1
                    return True
        return False

    def queue_size(self) -> int:
        with self._lock:
            return len(self._queue)

    def stats(self) -> Dict[str, Any]:
        return {
            "queue_size": self.queue_size(),
            "total_submitted": self.total_submitted,
            "total_processed": self.total_processed,
            "total_cancelled": self.total_cancelled,
            "max_queue_size": self.max_queue_size,
        }

    class SubmittedTask:
        """A submitted but possibly not-yet-processed task."""

        def __init__(self, fn: Callable[..., T], args: tuple, kwargs: dict) -> None:
            self.fn = fn
            self.args = args
            self.kwargs = kwargs


class Runtime:
    """Hardware-aware runtime used by inference and simulation components."""

    def __init__(self, config: Optional[RuntimeConfig] = None) -> None:
        self.config = config or RuntimeConfig.from_env()
        self.profile = detect_hardware_profile()
        self.capabilities = detect_capabilities()
        self.backends = BackendManager()
        self.backends.select(preferred=self.config.device if self.config.device != "auto" else None)
        self.compilation = CompilationManager(mode=self.config.compile)
        self.cache = ModelCache(max_size=self.config.max_cached_models)
        self.memory_monitor = MemoryMonitor()
        self.eviction = ModelEvictionManager(
            self.cache,
            monitor=self.memory_monitor,
            max_models=self.config.max_cached_models,
        )
        self.embedding_cache: Optional[LRUCache] = None
        self.reasoning_cache: Optional[LRUCache] = None
        if self.config.enable_embedding_cache:
            self.embedding_cache = LRUCache(max_size=1024)
        if self.config.enable_reasoning_cache:
            self.reasoning_cache = LRUCache(max_size=512)
        self.scheduler = InferenceScheduler()
        self._torch = None
        self._backend = self._detect_backend()
        self._dtype = self._resolve_precision()
        self._device = self._resolve_device()

    # ------------------------------------------------------------------
    # Device / backend detection
    # ------------------------------------------------------------------
    def _detect_backend(self) -> str:
        if self.config.device and self.config.device.lower() not in {"auto", ""}:
            return self.config.device.lower()
        return self.backends.preferred

    def _resolve_precision(self) -> str:
        return select_precision(self.profile, self.config.precision)

    def _resolve_device(self) -> str:
        if self.config.device and self.config.device.lower() not in {"auto", ""}:
            return self.config.device.lower()
        if self.profile.device_type == DeviceType.CUDA.value:
            return "cuda"
        if self.profile.device_type == DeviceType.MPS.value:
            return "mps"
        if self.profile.device_type == DeviceType.ROCM.value:
            return "rocm"
        return "cpu"

    def get_device(self) -> str:
        return self._device

    def get_device_info(self) -> Dict[str, object]:
        return to_device_info(self.profile)

    def get_backend(self) -> str:
        return self._backend

    def get_backend_info(self) -> Dict[str, object]:
        return {
            name: info.to_dict()
            for name, info in self.backends.get_available().items()
        }

    def get_capabilities(self) -> Dict[str, Any]:
        return self.capabilities.to_dict()

    def is_gpu_available(self) -> bool:
        return self.profile.device_type in {
            DeviceType.CUDA.value,
            DeviceType.ROCM.value,
            DeviceType.MPS.value,
        }

    def is_cuda_available(self) -> bool:
        return self.profile.device_type == DeviceType.CUDA.value

    def is_mps_available(self) -> bool:
        return self.profile.device_type == DeviceType.MPS.value

    def is_rocm_available(self) -> bool:
        return self.profile.device_type == DeviceType.ROCM.value

    def is_onnx_available(self) -> bool:
        return self.backends.is_available("onnx")

    def supports_bfloat16(self) -> bool:
        return self.profile.supports_bf16

    def supports_float16(self) -> bool:
        return self.profile.supports_fp16

    def supports_compile(self) -> bool:
        return self.profile.supports_compile

    def available_memory(self) -> int:
        return self.profile.available_memory or self.profile.total_memory or 0

    def get_memory_stats(self) -> Dict[str, Any]:
        return self.memory_monitor.get_stats()

    # ------------------------------------------------------------------
    # Batch size recommendation
    # ------------------------------------------------------------------
    def recommended_batch_size(
        self, *, model: Optional[Any] = None, sequence_length: int = 128
    ) -> int:
        available_memory = self.available_memory()
        if available_memory <= 0:
            available_memory = self.profile.ram_bytes or 0
        return recommended_batch_size(
            available_memory=available_memory,
            fallback=1,
            max_batch_size=self.config.max_batch_size,
        )

    # ------------------------------------------------------------------
    # Model preparation / lifecycle
    # ------------------------------------------------------------------
    def prepare_model(
        self,
        model: Any,
        *,
        model_id: Optional[str] = None,
        warmup: bool = False,
        compile_model: Optional[bool] = None,
    ) -> Any:
        """Move a model to the selected device, set precision, and optionally warm up."""
        self._torch = self._load_torch()
        model_key = model_id or getattr(model, "model_id", type(model).__name__)
        self.eviction.touch(model_key)
        self.cache.set_state(model_key, ModelState.LOADING.value)

        if self._torch is not None:
            if hasattr(model, "eval"):
                try:
                    model.eval()
                except Exception:
                    pass
            if hasattr(model, "to"):
                try:
                    device = self._torch.device(self._device)
                    model.to(device=device)
                except Exception:
                    pass
            if self._dtype in {"fp16", "bf16"} and hasattr(model, "to"):
                try:
                    dtype = self._get_torch_dtype(self._dtype)
                    model.to(dtype=dtype)
                except Exception:
                    pass

        # Optional compilation
        should_compile = (
            compile_model if compile_model is not None else self.config.compile != "off"
        )
        if should_compile and self.supports_compile():
            model = self.compilation.compile(model, model_id=model_key)

        # Warmup
        if warmup or self.config.warmup_enabled:
            self.warmup_model(model, model_id=model_key)
            self.cache.set_state(model_key, ModelState.WARM.value)
        else:
            self.cache.set_state(model_key, ModelState.READY.value)

        if model_id is not None:
            self.cache.put(model_id, model)
        self.eviction.evict_if_needed()
        return model

    def warmup_model(self, model: Any, *, model_id: Optional[str] = None) -> Any:
        """Run a small warmup inference to initialize CUDA kernels / memory pools."""
        if not callable(model):
            return model
        with self.inference_mode():
            try:
                model([0])
            except TypeError:
                try:
                    model(0)
                except Exception:
                    pass
        if model_id is not None:
            self.cache.set_state(model_id, ModelState.WARM.value)
        return model

    def release_model(self, model_id: str) -> None:
        """Release a model from cache (evicts from memory)."""
        self.cache.remove(model_id)

    def reload_model(self, model_id: str, loader: Callable[[], Any]) -> Any:
        """Reload a model from its loader."""
        self.cache.remove(model_id)
        return self.cache.get_or_load(model_id, loader)

    def evict_idle_models(self, idle_threshold_seconds: float = 300.0) -> int:
        """Evict models that have been idle for too long."""
        stats = self.cache.stats()
        evicted = 0
        # Simple LRU-based eviction using eviction manager
        evicted += self.eviction.evict_if_needed()
        return evicted

    # ------------------------------------------------------------------
    # Inference
    # ------------------------------------------------------------------
    def inference_mode(self) -> Any:
        if self._torch is None:
            self._torch = self._load_torch()
        if self._torch is None:
            return contextlib.nullcontext()
        try:
            return self._torch.inference_mode()
        except AttributeError:
            return self._torch.no_grad()

    def run_inference(
        self,
        model: Any,
        inputs: Any,
        *,
        model_id: Optional[str] = None,
        batch_size: Optional[int] = None,
        priority: str = Priority.NORMAL.value,
    ) -> Any:
        model_key = model_id or getattr(model, "model_id", type(model).__name__)
        self.eviction.touch(model_key)
        self.cache.set_state(model_key, ModelState.ACTIVE.value)

        # Check embedding cache for string inputs
        if self.embedding_cache is not None and isinstance(inputs, str):
            cache_key = f"{model_key}:{hash(inputs)}"
            cached = self.embedding_cache.get(cache_key)
            if cached is not None:
                return cached

        self.prepare_model(model, model_id=model_id, warmup=False)

        result = self._dispatch_inference(model, inputs, batch_size=batch_size)

        if self.embedding_cache is not None and isinstance(inputs, str):
            cache_key = f"{model_key}:{hash(inputs)}"
            self.embedding_cache.put(cache_key, result)

        return result

    def _dispatch_inference(
        self,
        model: Any,
        inputs: Any,
        *,
        batch_size: Optional[int] = None,
    ) -> Any:
        """Dispatch inference to the execution runtime with proper batching."""
        # If a list of multiple items and batching requested, use batch dispatch
        if (
            isinstance(inputs, Sequence)
            and not isinstance(inputs, (str, bytes, bytearray))
            and len(inputs) > 1
            and batch_size
        ):
            return batch_inference(
                lambda value: self._invoke(model, value),
                list(inputs),
                batch_size=batch_size,
            )
        return self._invoke(model, inputs)

    def _invoke(self, model: Any, inputs: Any) -> Any:
        with self.inference_mode():
            try:
                return model(inputs)
            except TypeError:
                try:
                    return model([inputs])
                except TypeError:
                    return model()

    def schedule_inference(
        self,
        model: Any,
        inputs: Any,
        *,
        model_id: Optional[str] = None,
        priority: str = Priority.NORMAL.value,
        batch_size: Optional[int] = None,
    ) -> InferenceScheduler.SubmittedTask:
        """Submit an inference request to the scheduler."""
        return self.scheduler.submit(
            self.run_inference,
            model,
            inputs,
            model_id=model_id,
            batch_size=batch_size,
            priority=priority,
        )

    # ------------------------------------------------------------------
    # Caching helpers
    # ------------------------------------------------------------------
    def cache_embedding(self, key: str, value: Any) -> None:
        if self.embedding_cache is not None:
            self.embedding_cache.put(key, value)

    def get_cached_embedding(self, key: str) -> Optional[Any]:
        if self.embedding_cache is not None:
            return self.embedding_cache.get(key)
        return None

    def cache_reasoning(self, key: str, value: Any) -> None:
        if self.reasoning_cache is not None:
            self.reasoning_cache.put(key, value)

    def get_cached_reasoning(self, key: str) -> Optional[Any]:
        if self.reasoning_cache is not None:
            return self.reasoning_cache.get(key)
        return None

    def invalidate_reasoning_cache(self) -> None:
        """Clear the reasoning cache (e.g., after important state changes)."""
        if self.reasoning_cache is not None:
            self.reasoning_cache.clear()

    def reasoning_hash(self, *components: Any) -> str:
        """Build a stable hash key for reasoning cache."""
        import hashlib

        h = hashlib.sha256()
        for component in components:
            h.update(str(component).encode("utf-8", errors="ignore"))
        return h.hexdigest()[:32]

    # ------------------------------------------------------------------
    # Utility
    # ------------------------------------------------------------------
    def _load_torch(self) -> Optional[Any]:
        try:
            import torch  # type: ignore

            return torch
        except ImportError:  # pragma: no cover - optional dependency
            return None

    def _get_torch_dtype(self, precision: str) -> Optional[Any]:
        if self._torch is None:
            self._torch = self._load_torch()
        if self._torch is None:
            return None
        dtype_map = {
            "fp16": self._torch.float16,
            "bf16": self._torch.bfloat16,
            "fp32": self._torch.float32,
        }
        return dtype_map.get(precision, self._torch.float32)

    def benchmark(self, *, samples: int = 3) -> Dict[str, Any]:
        def fn(value: Any) -> Any:
            return value + 1

        start = time.perf_counter()
        for _ in range(max(1, samples)):
            self.run_inference(fn, [1, 2, 3], batch_size=2)
        elapsed = time.perf_counter() - start
        return {
            "backend": self.get_backend(),
            "device": self.get_device(),
            "precision": self._dtype,
            "latency_seconds": elapsed / max(1, samples),
            "samples": samples,
            "cached_models": self.cache.stats()["cached_models"],
            "backend_info": self.get_backend_info(),
            "capabilities": self.get_capabilities(),
            "memory_stats": self.get_memory_stats(),
        }


class ModelRuntime:
    """Model lifecycle runtime that caches and reuses models."""

    def __init__(self, runtime: Optional[Runtime] = None) -> None:
        self.runtime = runtime or Runtime()
        self.cache = self.runtime.cache

    def load(self, model_id: str, model: Any, *, warmup: bool = False) -> Any:
        return self.runtime.prepare_model(model, model_id=model_id, warmup=warmup)

    def unload(self, model_id: str) -> None:
        self.runtime.release_model(model_id)

    def get(self, model_id: str) -> Optional[Any]:
        return self.cache.get(model_id)

    def get_state(self, model_id: str) -> str:
        return self.cache.get_state(model_id)

    def warmup(self, model_id: str) -> Any:
        model = self.cache.get(model_id)
        if model is not None:
            return self.runtime.warmup_model(model, model_id=model_id)
        return None

    def generate(self, model_id: str, inputs: Any, *, model: Optional[Any] = None, batch_size: Optional[int] = None, priority: str = Priority.NORMAL.value) -> Any:
        if model is not None:
            self.load(model_id, model)
        cached_model = self.get(model_id)
        if cached_model is None:
            raise KeyError(f"No model cached for {model_id}")
        return self.runtime.run_inference(cached_model, inputs, model_id=model_id, batch_size=batch_size, priority=priority)

    def embed(self, model_id: str, text: Any, *, model: Optional[Any] = None) -> Any:
        return self.generate(model_id, text, model=model)

    def encode(self, model_id: str, inputs: Any, *, model: Optional[Any] = None) -> Any:
        return self.generate(model_id, inputs, model=model)

    def batch(self, model_id: str, inputs: Sequence[Any], *, model: Optional[Any] = None, batch_size: Optional[int] = None) -> List[Any]:
        if model is not None:
            self.load(model_id, model)
        cached_model = self.get(model_id)
        if cached_model is None:
            raise KeyError(f"No model cached for {model_id}")
        return self.runtime.run_inference(cached_model, list(inputs), model_id=model_id, batch_size=batch_size)

    def profile(self) -> Dict[str, Any]:
        return {
            "backend": self.runtime.get_backend(),
            "device": self.runtime.get_device(),
            "precision": self.runtime._dtype,
            "cache": self.cache.stats(),
            "capabilities": self.runtime.get_capabilities(),
        }

    def get_stats(self) -> Dict[str, Any]:
        return self.profile()


def benchmark_hardware(config: Optional[RuntimeConfig] = None) -> Dict[str, Any]:
    """Run a hardware benchmark and return a report."""
    runtime = Runtime(config=config)
    report = runtime.benchmark()
    # Extend with a real representative workload
    import numpy as np

    # Matrix multiply benchmark
    start = time.perf_counter()
    a = np.random.rand(64, 64).astype(np.float32)
    b = np.random.rand(64, 64).astype(np.float32)
    for _ in range(10):
        np.dot(a, b)
    matmul_latency = (time.perf_counter() - start) / 10

    report["matmul_latency_ms"] = matmul_latency * 1000
    report["cpu_count"] = runtime.profile.cpu_count
    report["ram_bytes"] = runtime.profile.ram_bytes
    report["backend_description"] = runtime.backends.describe()
    return report