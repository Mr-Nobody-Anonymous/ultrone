from __future__ import annotations

import contextlib
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Sequence, TypeVar

from .batching import batch_inference, recommended_batch_size
from .compilation import CompilationManager
from .device import DeviceType, HardwareProfile, detect_hardware_profile, to_device_info
from .precision import PrecisionMode, PrecisionPolicy, select_precision

T = TypeVar("T")


@dataclass
class RuntimeConfig:
    device: str = "auto"
    precision: str = PrecisionMode.AUTO.value
    compile: str = "auto"
    quantization: str = "auto"
    max_batch_size: int = 8
    inference_timeout: float = 5.0
    enable_model_cache: bool = True
    enable_embedding_cache: bool = True
    enable_reasoning_cache: bool = True
    enable_async_inference: bool = True
    enable_xai: bool = False
    reasoning_interval: int = 5


class ModelCache:
    """Minimal model cache keyed by model_id."""

    def __init__(self) -> None:
        self._models: Dict[str, Any] = {}
        self._metadata: Dict[str, Dict[str, Any]] = {}

    def get(self, model_id: str) -> Optional[Any]:
        return self._models.get(model_id)

    def put(self, model_id: str, model: Any, **metadata: Any) -> Any:
        self._models[model_id] = model
        self._metadata[model_id] = metadata
        return model

    def get_or_load(self, model_id: str, loader: Callable[[], Any], *args: Any, **kwargs: Any) -> Any:
        cached = self.get(model_id)
        if cached is not None:
            return cached
        model = loader(*args, **kwargs)
        return self.put(model_id, model, **kwargs)

    def remove(self, model_id: str) -> None:
        self._models.pop(model_id, None)
        self._metadata.pop(model_id, None)

    def clear(self) -> None:
        self._models.clear()
        self._metadata.clear()

    def stats(self) -> Dict[str, Any]:
        return {"cached_models": len(self._models), "keys": sorted(self._models.keys())}


class Runtime:
    """Hardware-aware runtime used by inference and simulation components."""

    def __init__(self, config: Optional[RuntimeConfig] = None) -> None:
        self.config = config or RuntimeConfig()
        self.profile = detect_hardware_profile()
        self.compilation = CompilationManager(mode=self.config.compile)
        self.cache = ModelCache()
        self._torch = None
        self._backend = self._detect_backend()
        self._dtype = self._resolve_precision()
        self._device = self._resolve_device()

    def _detect_backend(self) -> str:
        if self.config.device and self.config.device.lower() not in {"auto", ""}:
            return self.config.device.lower()
        return self.profile.device_type

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

    def is_gpu_available(self) -> bool:
        return self.profile.device_type in {DeviceType.CUDA.value, DeviceType.ROCM.value, DeviceType.MPS.value}

    def is_cuda_available(self) -> bool:
        return self.profile.device_type == DeviceType.CUDA.value

    def is_mps_available(self) -> bool:
        return self.profile.device_type == DeviceType.MPS.value

    def supports_bfloat16(self) -> bool:
        return self.profile.supports_bf16

    def supports_float16(self) -> bool:
        return self.profile.supports_fp16

    def supports_compile(self) -> bool:
        return self.profile.supports_compile

    def available_memory(self) -> int:
        return self.profile.available_memory or self.profile.total_memory or 0

    def recommended_batch_size(self, *, model: Optional[Any] = None, sequence_length: int = 128) -> int:
        available_memory = self.available_memory()
        if available_memory <= 0:
            available_memory = self.profile.ram_bytes or 0
        return recommended_batch_size(
            available_memory=available_memory,
            fallback=1,
            max_batch_size=self.config.max_batch_size,
        )

    def prepare_model(self, model: Any, *, model_id: Optional[str] = None, warmup: bool = False) -> Any:
        self._torch = self._load_torch()
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
        if model_id is not None:
            self.cache.put(model_id, model)
        if warmup:
            self.warmup_model(model, model_id=model_id)
        return model

    def warmup_model(self, model: Any, *, model_id: Optional[str] = None) -> Any:
        if not callable(model):
            return model
        try:
            model([0])
        except TypeError:
            try:
                model(0)
            except Exception:
                pass
        if model_id is not None:
            self.cache.put(model_id, model)
        return model

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
    ) -> Any:
        self.prepare_model(model, model_id=model_id, warmup=False)
        if isinstance(inputs, Sequence) and not isinstance(inputs, (str, bytes, bytearray)) and len(inputs) > 1 and batch_size:
            return batch_inference(lambda value: self._invoke(model, value), list(inputs), batch_size=batch_size)
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

    def _load_torch(self) -> Optional[Any]:
        try:
            import torch  # type: ignore

            return torch
        except ImportError:  # pragma: no cover - optional dependency
            return None

    def _get_torch_dtype(self, precision: str) -> Any:
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
        }


class ModelRuntime:
    """Model lifecycle runtime that caches and reuses models."""

    def __init__(self, runtime: Optional[Runtime] = None) -> None:
        self.runtime = runtime or Runtime()
        self.cache = self.runtime.cache

    def load(self, model_id: str, model: Any, *, warmup: bool = False) -> Any:
        return self.runtime.prepare_model(model, model_id=model_id, warmup=warmup)

    def unload(self, model_id: str) -> None:
        self.cache.remove(model_id)

    def get(self, model_id: str) -> Optional[Any]:
        return self.cache.get(model_id)

    def generate(self, model_id: str, inputs: Any, *, model: Optional[Any] = None, batch_size: Optional[int] = None) -> Any:
        if model is not None:
            self.load(model_id, model)
        cached_model = self.get(model_id)
        if cached_model is None:
            raise KeyError(f"No model cached for {model_id}")
        return self.runtime.run_inference(cached_model, inputs, model_id=model_id, batch_size=batch_size)

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
        }


def benchmark_hardware(config: Optional[RuntimeConfig] = None) -> Dict[str, Any]:
    runtime = Runtime(config=config)
    return runtime.benchmark()
