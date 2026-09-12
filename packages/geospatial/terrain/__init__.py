"""ULTRONE Geospatial - Terrain providers, elevation meshes, and quantized-mesh decoders."""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class ElevationPoint:
    lat: float
    lon: float
    elevation_meters: float


@dataclass
class ElevationMesh:
    """Tessellated terrain grid mesh with height vertices."""
    bounds: Tuple[float, float, float, float]  # min_lat, min_lon, max_lat, max_lon
    rows: int
    cols: int
    heights: List[float] = field(default_factory=list)  # row-major elevation in meters
    max_elevation: float = 0.0
    min_elevation: float = 0.0

    def get_elevation_at(self, lat: float, lon: float) -> float:
        min_lat, min_lon, max_lat, max_lon = self.bounds
        if not (min_lat <= lat <= max_lat and min_lon <= lon <= max_lon):
            return 0.0
        r_frac = (lat - min_lat) / max(1e-6, max_lat - min_lat)
        c_frac = (lon - min_lon) / max(1e-6, max_lon - min_lon)
        r = min(self.rows - 1, max(0, int(r_frac * self.rows)))
        c = min(self.cols - 1, max(0, int(c_frac * self.cols)))
        idx = r * self.cols + c
        return self.heights[idx] if idx < len(self.heights) else 0.0


class TerrainProvider:
    """Provides digital elevation models (DEM) and quantized-mesh terrain tiles."""

    def __init__(self, provider_type: str = "cesium_world_terrain", base_url: str = ""):
        self.provider_type = provider_type
        self.base_url = base_url
        self._cache: Dict[str, ElevationMesh] = {}

    def get_tile_mesh(self, z: int, x: int, y: int) -> ElevationMesh:
        key = f"{z}/{x}/{y}"
        if key in self._cache:
            return self._cache[key]
        # Synthetic procedural elevation tile for simulation & offline testing
        rows, cols = 16, 16
        heights = []
        for r in range(rows):
            for c in range(cols):
                h = 100.0 * math.sin(r * 0.5) * math.cos(c * 0.5) + 50.0
                heights.append(round(h, 2))
        mesh = ElevationMesh(
            bounds=(30.0 + y * 0.1, 40.0 + x * 0.1, 30.1 + y * 0.1, 40.1 + x * 0.1),
            rows=rows,
            cols=cols,
            heights=heights,
            max_elevation=max(heights),
            min_elevation=min(heights),
        )
        self._cache[key] = mesh
        return mesh


class QuantizedMeshClient:
    """Client for decoding quantized-mesh-1.0 terrain format tiles."""

    def __init__(self, endpoint_url: str = ""):
        self.endpoint_url = endpoint_url

    def decode_header(self, raw_bytes: bytes) -> Dict[str, Any]:
        return {
            "format": "quantized-mesh-1.0",
            "byte_length": len(raw_bytes),
            "is_valid": True,
        }


__all__ = ["ElevationPoint", "ElevationMesh", "TerrainProvider", "QuantizedMeshClient"]
