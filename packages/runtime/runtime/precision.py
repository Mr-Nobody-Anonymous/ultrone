from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional

from .device import DeviceType, HardwareProfile


class PrecisionMode(str, Enum):
    AUTO = "auto"
    FP32 = "fp32"
    FP16 = "fp16"
    BF16 = "bf16"
    INT8 = "int8"


@dataclass(frozen=True)
class PrecisionPolicy:
    mode: str = PrecisionMode.AUTO.value
    fallback: str = PrecisionMode.FP32.value

    @classmethod
    def from_value(cls, value: Optional[str]) -> "PrecisionPolicy":
        if not value:
            return cls()
        value = value.lower()
        if value in {PrecisionMode.AUTO.value, ""}:
            return cls(mode=PrecisionMode.AUTO.value)
        if value in {PrecisionMode.FP32.value, "float32"}:
            return cls(mode=PrecisionMode.FP32.value)
        if value in {PrecisionMode.FP16.value, "float16"}:
            return cls(mode=PrecisionMode.FP16.value)
        if value in {PrecisionMode.BF16.value, "bfloat16"}:
            return cls(mode=PrecisionMode.BF16.value)
        if value in {PrecisionMode.INT8.value, "int8"}:
            return cls(mode=PrecisionMode.INT8.value)
        return cls(mode=PrecisionMode.AUTO.value)

    def resolve(self, profile: HardwareProfile) -> str:
        if self.mode != PrecisionMode.AUTO.value:
            return self.mode
        if profile.device_type == DeviceType.CUDA.value and profile.supports_bf16:
            return PrecisionMode.BF16.value
        if profile.device_type in {DeviceType.CUDA.value, DeviceType.MPS.value, DeviceType.ROCM.value} and profile.supports_fp16:
            return PrecisionMode.FP16.value
        return self.fallback


def select_precision(profile: HardwareProfile, mode: Optional[str] = None) -> str:
    policy = PrecisionPolicy.from_value(mode)
    return policy.resolve(profile)
