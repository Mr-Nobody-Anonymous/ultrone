# Copyright (c) Ultrone Contributors. All rights reserved.
"""2D Vector Map Engine definitions (MapLibre / Canvas)."""
from dataclasses import dataclass


@dataclass
class Map2DConfig:
    style_url: str = "https://demotiles.maplibre.org/style.json"
    default_center_lat: float = 34.05
    default_center_lng: float = -118.25
    default_zoom: float = 1.0
    interactive: bool = True
