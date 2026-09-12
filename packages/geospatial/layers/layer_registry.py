# Copyright (c) Ultrone Contributors. All rights reserved.
"""Geospatial Layer Registry.

Separates map visualization into 4 canonical tiers:
1. Base Map (Streets, Satellite, Terrain, Dark Vector)
2. Object Layers (Sensors, Vehicles, Infrastructure, Simulated entities)
3. Environment Layers (Elevation, Weather, Radar coverage cones)
4. Analytics Overlays (Density heatmaps, Predictive track corridors, Areas of interest)
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


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
    provider: str = "open_source"   # e.g., 'osm', 'maptiler', 'cesium', 'world_model'
    source_url: str = ""
    properties: Dict[str, Any] = field(default_factory=dict)


CANONICAL_LAYERS: List[LayerDefinition] = [
    # Tier 1: Base Map
    LayerDefinition("base-dark", "Dark Vector", LayerCategory.BASE_MAP, LayerType.VECTOR, enabled=True, opacity=1.0, z_index=0),
    LayerDefinition("base-satellite", "Satellite Imagery", LayerCategory.BASE_MAP, LayerType.RASTER, enabled=False, opacity=1.0, z_index=1),
    LayerDefinition("base-terrain", "3D Terrain Elevation", LayerCategory.BASE_MAP, LayerType.TERRAIN_3D, enabled=True, opacity=1.0, z_index=2),

    # Tier 2: Entities
    LayerDefinition("ent-sensors", "Sensor Nodes", LayerCategory.OBJECTS, LayerType.GEOJSON, enabled=True, opacity=1.0, z_index=10),
    LayerDefinition("ent-air", "Air Assets & UAVs", LayerCategory.OBJECTS, LayerType.GEOJSON, enabled=True, opacity=1.0, z_index=11),
    LayerDefinition("ent-ground", "Ground Vehicles", LayerCategory.OBJECTS, LayerType.GEOJSON, enabled=True, opacity=1.0, z_index=12),
    LayerDefinition("ent-sim", "Simulated Assets", LayerCategory.OBJECTS, LayerType.GEOJSON, enabled=True, opacity=0.85, z_index=13),

    # Tier 3: Environment
    LayerDefinition("env-radar-cones", "Radar Coverage Arcs", LayerCategory.ENVIRONMENT, LayerType.GEOJSON, enabled=True, opacity=0.25, z_index=20),
    LayerDefinition("env-weather-ecm", "Weather / ECM Clouds", LayerCategory.ENVIRONMENT, LayerType.RASTER, enabled=False, opacity=0.45, z_index=21),

    # Tier 4: Analytics
    LayerDefinition("anl-density", "Contact Density Heatmap", LayerCategory.ANALYTICS, LayerType.HEATMAP, enabled=False, opacity=0.6, z_index=30),
    LayerDefinition("anl-trajectories", "Extrapolated Vectors", LayerCategory.ANALYTICS, LayerType.VECTOR, enabled=True, opacity=0.75, z_index=31),
    LayerDefinition("anl-corridors", "Protected Corridors", LayerCategory.ANALYTICS, LayerType.GEOJSON, enabled=True, opacity=0.3, z_index=32),
]


class LayerRegistry:
    """Registry maintaining active layer state."""

    def __init__(self, initial_layers: Optional[List[LayerDefinition]] = None) -> None:
        self._layers: Dict[str, LayerDefinition] = {
            l.id: l for l in (initial_layers or CANONICAL_LAYERS)
        }

    def get_layer(self, layer_id: str) -> Optional[LayerDefinition]:
        return self._layers.get(layer_id)

    def list_all(self) -> List[LayerDefinition]:
        return sorted(self._layers.values(), key=lambda l: l.z_index)

    def set_visibility(self, layer_id: str, enabled: bool) -> None:
        if layer_id in self._layers:
            self._layers[layer_id].enabled = enabled

    def set_opacity(self, layer_id: str, opacity: float) -> None:
        if layer_id in self._layers:
            self._layers[layer_id].opacity = max(0.0, min(1.0, opacity))
