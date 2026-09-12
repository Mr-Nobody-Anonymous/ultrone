# Copyright (c) Ultrone Contributors. All rights reserved.
"""Layer styling, color mapping, and symbology."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class LayerStyle:
    stroke_color: str = "#38bdf8"
    stroke_width: float = 1.5
    fill_color: str = "rgba(56, 189, 248, 0.2)"
    point_radius: float = 5.0
    dash_pattern: str = ""
