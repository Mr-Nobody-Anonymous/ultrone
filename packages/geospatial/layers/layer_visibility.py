# Copyright (c) Ultrone Contributors. All rights reserved.
"""Layer visibility state manager."""
from __future__ import annotations

from typing import Dict


class LayerVisibilityManager:
    """Manages layer visibility and opacity states."""

    def __init__(self) -> None:
        self._visibility: Dict[str, bool] = {}
        self._opacity: Dict[str, float] = {}

    def set_visibility(self, layer_id: str, visible: bool) -> None:
        self._visibility[layer_id] = visible

    def is_visible(self, layer_id: str, default: bool = True) -> bool:
        return self._visibility.get(layer_id, default)

    def set_opacity(self, layer_id: str, opacity: float) -> None:
        self._opacity[layer_id] = max(0.0, min(1.0, opacity))

    def get_opacity(self, layer_id: str, default: float = 1.0) -> float:
        return self._opacity.get(layer_id, default)
