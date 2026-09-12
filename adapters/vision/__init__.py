# Copyright (c) Ultrone Contributors. All rights reserved.
"""Vision adapters — port for perception model providers.

Concrete wiring should wrap ``backend.vision`` (object detector, satellite
processor, terrain vision, thermal processor) and ``brain.perception``.
"""
from adapters.base import BaseAdapter, unavailable
from typing import Any, Dict

__all__ = ["VisionAdapter"]


class VisionAdapter(BaseAdapter):
    """Port every vision provider implementation must satisfy."""

    name = "vision"

    def connect(self) -> bool:  # pragma: no cover - placeholder
        return False

    def close(self) -> None:  # pragma: no cover - placeholder
        pass

    def health(self) -> Dict[str, Any]:  # pragma: no cover - placeholder
        return unavailable("no provider implementation wired; see "
                           "backend/vision and brain/perception")
