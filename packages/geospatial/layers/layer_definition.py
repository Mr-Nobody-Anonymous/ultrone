# Copyright (c) Ultrone Contributors. All rights reserved.
"""Layer definitions and types for geospatial visualization."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict


class LayerCategory(str, Enum):
    BASE_MAP = "base_map"
    OBJECTS = "objects"
    ENVIRONMENT = "environment"
    ANALYTICS = "analytics"


class LayerType(str, Enum):
    RASTER = "raster"
    VECTOR = "vector"
    TERRAIN_3D = "terrain_3d"
    TILES_3D = "tiles_3d"
    GEOJSON = "geojson"
    HEATMAP = "heatmap"


@dataclass
class LayerDefinition:
    """Definition of a geospatial visualization layer."""
    id: str
    name: str
    category: LayerCategory
    layer_type: LayerType
    enabled: bool = True
    opacity: float = 1.0
    z_index: int = 0
    provider: str = "open_source"
    source_url: str = ""
    properties: Dict[str, Any] = field(default_factory=dict)
