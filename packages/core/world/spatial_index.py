# Copyright (c) Ultrone Contributors. All rights reserved.
"""Spatial indexing for fast bounding box and radius queries."""
from __future__ import annotations

import math
from typing import List, Tuple
from packages.core.entities import Entity


class SpatialIndex:
    """Grid-based spatial index for fast 2D geodetic contact queries."""

    def __init__(self, cell_size_deg: float = 0.5) -> None:
        self.cell_size = cell_size_deg
        self._grid: dict[Tuple[int, int], List[Entity]] = {}

    def _hash(self, lat: float, lng: float) -> Tuple[int, int]:
        return (int(math.floor(lat / self.cell_size)), int(math.floor(lng / self.cell_size)))

    def index_entities(self, entities: List[Entity]) -> None:
        """Re-index a list of entities."""
        self._grid.clear()
        for ent in entities:
            if ent.position:
                key = self._hash(ent.position.lat, ent.position.lng)
                self._grid.setdefault(key, []).append(ent)

    def query_radius(self, lat: float, lng: float, radius_km: float) -> List[Entity]:
        """Find entities within a given radius in kilometers."""
        deg_radius = radius_km / 111.0
        min_key = self._hash(lat - deg_radius, lng - deg_radius)
        max_key = self._hash(lat + deg_radius, lng + deg_radius)

        results: List[Entity] = []
        for x in range(min_key[0], max_key[0] + 1):
            for y in range(min_key[1], max_key[1] + 1):
                for ent in self._grid.get((x, y), []):
                    if ent.position:
                        dlat = (ent.position.lat - lat) * 111.0
                        dlng = (ent.position.lng - lng) * 111.0 * math.cos(math.radians(lat))
                        dist = math.hypot(dlat, dlng)
                        if dist <= radius_km:
                            results.append(ent)
        return results
