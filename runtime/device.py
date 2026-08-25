from __future__ import annotations

import os
from dataclasses import dataclass
from enum import Enum
from typing import Dict, Optional


class DeviceType(str, Enum):
    CPU = "cpu"
    CUDA = "cuda"
    ROCM = "rocm"
    MPS = "mps"
    OTHER = "other"


@dataclass(frozen=True)
class HardwareProfile:
    device_type: str
    device_name: str
    total_memory: int = 0
    available_memory: int = 0
    compute_capability: Optional[str] = None
    supports_fp16: bool = False
    supports_bf16: bool = False
    supports_int8: bool = False
    supports_compile: bool = False
    cpu_count: int = 1
    ram_bytes: int = 0


def detect_hardware_profile() -> HardwareProfile:
    """Detect the best available execution device without hard-failing."""
    cpu_count = os.cpu_count() or 1
    ram_bytes = _get_ram_bytes()

    try:
        import torch  # type: ignore
    except ImportError:  # pragma: no cover - optional dependency
        torch = None

    if torch is not None:
        if getattr(torch, "cuda", None) is not None and torch.cuda.is_available():
            try:
                device = torch.device("cuda")
                props = torch.cuda.get_device_properties(device)
                total_memory = int(getattr(props, "total_memory", 0) or 0)
                available_memory = max(total_memory, int(torch.cuda.mem_get_info()[0]))
                return HardwareProfile(
                    device_type=DeviceType.CUDA.value,
                    device_name=getattr(props, "name", "NVIDIA GPU"),
                    total_memory=total_memory,
                    available_memory=available_memory,
                    compute_capability=getattr(props, "major", None) and f"{props.major}.{props.minor}",
                    supports_fp16=True,
                    supports_bf16=getattr(torch.cuda, "is_bf16_supported", lambda *args, **kwargs: False)(),
                    supports_int8=True,
                    supports_compile=hasattr(torch, "compile"),
                    cpu_count=cpu_count,
                    ram_bytes=ram_bytes,
                )
            except Exception:
                pass

        if getattr(torch.backends, "mps", None) is not None and torch.backends.mps.is_available():
            return HardwareProfile(
                device_type=DeviceType.MPS.value,
                device_name="Apple Metal",
                total_memory=0,
                available_memory=0,
                supports_fp16=True,
                supports_bf16=False,
                supports_int8=False,
                supports_compile=False,
                cpu_count=cpu_count,
                ram_bytes=ram_bytes,
            )

        # ROCm detection: verify an actual device is available, not just a HIP build
        is_rocm_build = bool(
            hasattr(torch.version, "hip")
            and getattr(torch.version, "hip", None) is not None
        )
        if is_rocm_build:
            # Check if a ROCm device is actually accessible
            rocm_available = False
            try:
                # On ROCm builds, torch.cuda.is_available() returns True when a GPU is present
                rocm_available = bool(torch.cuda.is_available())
            except Exception:
                rocm_available = False
            if rocm_available:
                try:
                    device = torch.device("cuda")
                    props = torch.cuda.get_device_properties(device)
                    total_memory = int(getattr(props, "total_memory", 0) or 0)
                    available_memory = max(total_memory, int(torch.cuda.mem_get_info()[0]))
                    return HardwareProfile(
                        device_type=DeviceType.ROCM.value,
                        device_name=getattr(props, "name", "AMD GPU"),
                        total_memory=total_memory,
                        available_memory=available_memory,
                        compute_capability=getattr(props, "major", None) and f"{props.major}.{props.minor}",
                        supports_fp16=True,
                        supports_bf16=False,
                        supports_int8=True,
                        supports_compile=hasattr(torch, "compile"),
                        cpu_count=cpu_count,
                        ram_bytes=ram_bytes,
                    )
                except Exception:
                    pass
            # ROCm build but no device available — fall through to CPU
            logger.debug("ROCm build detected but no GPU device available; falling back to CPU")

    return HardwareProfile(
        device_type=DeviceType.CPU.value,
        device_name="CPU",
        total_memory=_get_available_cpu_memory(),
        available_memory=_get_available_cpu_memory(),
        supports_fp16=False,
        supports_bf16=False,
        supports_int8=False,
        supports_compile=False,
        cpu_count=cpu_count,
        ram_bytes=ram_bytes,
    )


def _get_ram_bytes() -> int:
    try:
        import psutil  # type: ignore

        return int(psutil.virtual_memory().total)
    except Exception:
        return 0


def _get_available_cpu_memory() -> int:
    try:
        import psutil  # type: ignore

        return int(psutil.virtual_memory().available)
    except Exception:
        return 0


def to_device_info(profile: HardwareProfile) -> Dict[str, object]:
    return {
        "device_type": profile.device_type,
        "device_name": profile.device_name,
        "total_memory": profile.total_memory,
        "available_memory": profile.available_memory,
        "compute_capability": profile.compute_capability,
        "supports_fp16": profile.supports_fp16,
        "supports_bf16": profile.supports_bf16,
        "supports_int8": profile.supports_int8,
        "supports_compile": profile.supports_compile,
        "cpu_count": profile.cpu_count,
        "ram_bytes": profile.ram_bytes,
    }
