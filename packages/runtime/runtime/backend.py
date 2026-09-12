from __future__ import annotations

"""Backend abstraction — unified interface over PyTorch, ONNX, and CPU fallbacks."""

import logging
from dataclasses import dataclass
from typing import Any, Callable, Dict, Optional

logger = logging.getLogger("Ultrone.Runtime.Backend")


@dataclass
class BackendInfo:
    """Information about an available execution backend."""

    name: str
    available: bool
    device: str = "cpu"
    reason: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "available": self.available,
            "device": self.device,
            "reason": self.reason,
        }


def detect_backends() -> Dict[str, BackendInfo]:
    """Detect which execution backends are available without importing unavailable packages.

    Returns
    -------
    Dict[str, BackendInfo]
        Mapping of backend name to availability info.
    """
    backends: Dict[str, BackendInfo] = {}

    # --- PyTorch ---
    try:
        import torch  # type: ignore

        has_cuda = bool(getattr(torch, "cuda", None) is not None and torch.cuda.is_available())
        has_mps = bool(
            getattr(torch.backends, "mps", None) is not None
            and torch.backends.mps.is_available()
        )
        is_rocm = bool(getattr(torch.version, "hip", None) is not None)
        backends["pytorch"] = BackendInfo(
            name="pytorch",
            available=True,
            device="cuda" if has_cuda else ("mps" if has_mps else "cpu"),
            reason="torch import succeeded",
        )
        backends["cuda"] = BackendInfo(
            name="cuda", available=has_cuda, device="cuda",
            reason="torch.cuda.is_available()" if has_cuda else "no CUDA device",
        )
        backends["rocm"] = BackendInfo(
            name="rocm", available=is_rocm, device="rocm",
            reason="torch.version.hip set" if is_rocm else "not a ROCm build",
        )
        backends["mps"] = BackendInfo(
            name="mps", available=has_mps, device="mps",
            reason="torch.backends.mps.is_available()" if has_mps else "no MPS device",
        )
    except ImportError:
        backends["pytorch"] = BackendInfo(
            name="pytorch", available=False, device="cpu", reason="torch not installed"
        )
        backends["cuda"] = BackendInfo(name="cuda", available=False, reason="torch not installed")
        backends["rocm"] = BackendInfo(name="rocm", available=False, reason="torch not installed")
        backends["mps"] = BackendInfo(name="mps", available=False, reason="torch not installed")

    # --- ONNX Runtime ---
    try:
        import onnxruntime as ort  # type: ignore

        available_providers = set(ort.get_available_providers())
        has_cuda = "CUDAExecutionProvider" in available_providers
        backends["onnx"] = BackendInfo(
            name="onnx",
            available=True,
            device="cuda" if has_cuda else "cpu",
            reason=f"providers={sorted(available_providers)}",
        )
    except ImportError:
        backends["onnx"] = BackendInfo(
            name="onnx", available=False, device="cpu", reason="onnxruntime not installed"
        )

    # --- CPU fallback (always available) ---
    backends["cpu"] = BackendInfo(
        name="cpu", available=True, device="cpu", reason="always available"
    )

    return backends


class BackendManager:
    """Selects and manages the best available execution backend."""

    def __init__(self) -> None:
        self._backends = detect_backends()
        self._preferred = "cpu"

    def get_available(self) -> Dict[str, BackendInfo]:
        return self._backends

    def select(self, preferred: Optional[str] = None) -> BackendInfo:
        """Select the best backend given a preference.

        Preference order: explicit preference → CUDA → ROCm → MPS → CPU.
        """
        if preferred and preferred.lower() in self._backends:
            info = self._backends[preferred.lower()]
            if info.available:
                self._preferred = info.name
                return info

        for name in ("cuda", "rocm", "mps", "cpu"):
            info = self._backends.get(name)
            if info is not None and info.available:
                self._preferred = name
                return info

        # CPU always available
        self._preferred = "cpu"
        return self._backends["cpu"]

    @property
    def preferred(self) -> str:
        return self._preferred

    def is_available(self, name: str) -> bool:
        info = self._backends.get(name)
        return info is not None and info.available

    def describe(self) -> str:
        """Human-readable description of selected backend decisions."""
        selected = self._backends.get(self._preferred)
        if selected is None:
            return "No backend selected"
        parts = [f"Selected backend: {selected.name} ({selected.device})"]
        if selected.reason:
            parts.append(f"Reason: {selected.reason}")
        unavailable = [n for n, i in self._backends.items() if not i.available and n != "cpu"]
        if unavailable:
            parts.append(f"Unavailable: {', '.join(unavailable)}")
        return "; ".join(parts)