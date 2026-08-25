from __future__ import annotations

"""Hardware capability profile — single source of truth for what the hardware can do."""

from dataclasses import dataclass
from typing import Any, Dict

from .device import HardwareProfile, detect_hardware_profile


@dataclass(frozen=True)
class Capabilities:
    """Structured hardware capability profile."""

    device_type: str
    device_name: str
    total_memory: int
    available_memory: int
    compute_capability: str | None
    supports_fp16: bool
    supports_bf16: bool
    supports_int8: bool
    supports_compile: bool
    cpu_count: int
    ram_bytes: int

    @classmethod
    def from_profile(cls, profile: HardwareProfile) -> "Capabilities":
        return cls(
            device_type=profile.device_type,
            device_name=profile.device_name,
            total_memory=profile.total_memory,
            available_memory=profile.available_memory,
            compute_capability=profile.compute_capability,
            supports_fp16=profile.supports_fp16,
            supports_bf16=profile.supports_bf16,
            supports_int8=profile.supports_int8,
            supports_compile=profile.supports_compile,
            cpu_count=profile.cpu_count,
            ram_bytes=profile.ram_bytes,
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "device_type": self.device_type,
            "device_name": self.device_name,
            "total_memory": self.total_memory,
            "available_memory": self.available_memory,
            "compute_capability": self.compute_capability,
            "supports_fp16": self.supports_fp16,
            "supports_bf16": self.supports_bf16,
            "supports_int8": self.supports_int8,
            "supports_compile": self.supports_compile,
            "cpu_count": self.cpu_count,
            "ram_bytes": self.ram_bytes,
        }


def detect_capabilities() -> Capabilities:
    """Detect hardware capabilities without importing unavailable packages."""
    return Capabilities.from_profile(detect_hardware_profile())