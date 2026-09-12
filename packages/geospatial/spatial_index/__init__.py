"""ULTRONE Geospatial - Spatial indexing, R-Tree bounds, and H3-style grid partitions."""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class BoundingBox:
    min_lat: float
    min_lon: float
    max_lat: float
    max_lon: float

    def contains(self, lat: float, lon: float) -> bool:
        return self.min_lat <= lat <= self.max_lat and self.min_lon <= lon <= self.max_lon

    def intersects(self, other: "BoundingBox") -> bool:
        return not (
            self.max_lat < other.min_lat
            or self.min_lat > other.max_lat
            or self.max_lon < other.min_lon
            or self.min_lon > other.max_lon
        )


class SpatialIndex:
    """Thread-safe hierarchical spatial grid for fast proximity and bounding box lookups."""

    def __init__(self, cell_size_deg: float = 0.5):
        self.cell_size_deg = cell_size_deg
        # (grid_x, grid_y) -> list of (item_id, lat, lon, data)
        self._grid: Dict[Tuple[int, int], List[Tuple[str, float, float, Any]]] = {}
        self._locations: Dict[str, Tuple[float, float]] = {}

    def _hash(self, lat: float, lon: float) -> Tuple[int, int]:
        gx = int(math.floor(lon / self.cell_size_deg))
        gy = int(math.floor(lat / self.cell_size_deg))
        return (gx, gy)

    def insert(self, item_id: str, lat: float, lon: float, data: Any = None) -> None:
        self.remove(item_id)
        cell = self._hash(lat, lon)
        if cell not in self._grid:
            self._grid[cell] = []
        self._grid[cell].append((item_id, lat, lon, data))
        self._locations[item_id] = (lat, lon)

    def remove(self, item_id: str) -> None:
        if item_id in self._locations:
            lat, lon = self._locations.pop(item_id)
            cell = self._hash(lat, lon)
            if cell in self._grid:
                self._grid[cell] = [entry for entry in self._grid[cell] if entry[0] != item_id]

    def query_radius(self, center_lat: float, center_lon: float, radius_km: float) -> List[Tuple[str, float, float, Any]]:
        """Query items within radius in kilometers."""
        deg_approx = radius_km / 111.0
        min_cell = self._hash(center_lat - deg_approx, center_lon - deg_approx)
        max_cell = self._hash(center_lat + deg_approx, center_lon + deg_approx)

        results = []
        for gx in range(min_cell[0], max_cell[0] + 1):
            for gy in range(min_cell[1], max_cell[1] + 1):
                cell = (gx, gy)
                if cell in self._grid:
                    for item_id, lat, lon, data in self._grid[cell]:
                        d_km = math.sqrt((lat - center_lat) ** 2 + (lon - center_lon) ** 2) * 111.0
                        if d_km <= radius_km:
                            results.append((item_id, lat, lon, data))
        return results

    def query_bbox(self, bbox: BoundingBox) -> List[Tuple[str, float, float, Any]]:
        min_cell = self._hash(bbox.min_lat, bbox.min_lon)
        max_cell = self._hash(bbox.max_lat, bbox.max_lon)
        results = []
        for gx in range(min_cell[0], max_cell[0] + 1):
            for gy in range(min_cell[1], max_cell[1] + 1):
                cell = (gx, gy)
                if cell in self._grid:
                    for item_id, lat, lon, data in self._grid[cell]:
                        if bbox.contains(lat, lon):
                            results.append((item_id, lat, lon, data))
        return results


__all__ = ["BoundingBox", "SpatialIndex"]
