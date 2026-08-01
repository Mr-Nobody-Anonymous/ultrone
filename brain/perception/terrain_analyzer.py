# Copyright (c) Ultrone Contributors. All rights reserved.
"""Terrain analyzer - 3D terrain elevation, slope, aspect, hillshade, viewshed.

Provides a full 3D model of the battlefield terrain:

- Elevation surface (heightmap) built from the terrain grid
- Slope (degrees) and aspect (compass direction of maximum downhill slope)
- Hillshade / relief shading for realistic 3D imaging
- Viewshed analysis: which cells are visible from a given observer position
- Heightmap export for the frontend Three.js renderer
"""

from __future__ import annotations

import logging
import math
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from data.terrain import Terrain, TerrainType, GridCell

logger = logging.getLogger("Ultrone.Brain.Perception.TerrainAnalyzer")


class TerrainAnalyzer:
    """
    Analyzes the 3D structure of battlefield terrain.

    Builds an elevation model (DEM) from the terrain grid and computes:
    - **Heightmap**: 2D array of elevations (ready for Three.js PlaneGeometry)
    - **Slope**: steepness in degrees at every cell
    - **Aspect**: downhill compass direction at every cell
    - **Hillshade**: shaded relief for visual rendering
    - **Viewshed**: visibility mask from an observer position (with optional
      observer height above ground and terrain-blow-through handling)
    """

    # Terrain types that block line of sight
    _LOS_BLOCKERS = {
        TerrainType.FOREST,
        TerrainType.URBAN,
        TerrainType.MOUNTAIN,
        TerrainType.HILLS,
    }

    def __init__(self, terrain: Optional[Terrain] = None) -> None:
        self.terrain = terrain
        self._elevation: Optional[np.ndarray] = None
        self._slope: Optional[np.ndarray] = None
        self._aspect: Optional[np.ndarray] = None
        self._hillshade: Optional[np.ndarray] = None
        self._cache_key: Optional[Tuple[int, int]] = None

    # ------------------------------------------------------------------
    # Heightmap / DEM
    # ------------------------------------------------------------------

    def _build_heightmap(self) -> np.ndarray:
        """Build a 2D elevation array from the terrain grid.

        Each cell's elevation is its base elevation plus a small
        per-terrain-type bump so that forests/urban appear above open
        ground in the 3D render.

        Returns (height, width) float array.
        """
        if self.terrain is None:
            return np.zeros((20, 20), dtype=np.float32)

        width_cells = self.terrain.get_width_cells()
        height_cells = self.terrain.get_height_cells()

        if width_cells <= 0 or height_cells <= 0:
            return np.zeros((20, 20), dtype=np.float32)

        dem = np.zeros((height_cells, width_cells), dtype=np.float32)

        # Terrain-type elevation bump (meters)
        type_bump = {
            TerrainType.OPEN: 0.0,
            TerrainType.PLAINS: 0.5,
            TerrainType.FOREST: 8.0,
            TerrainType.URBAN: 15.0,
            TerrainType.MOUNTAIN: 60.0,
            TerrainType.HILLS: 25.0,
            TerrainType.DESERT: 2.0,
            TerrainType.WATER: -5.0,
            TerrainType.COASTAL: 1.0,
            TerrainType.SUBMERGED: -12.0,
        }

        for y in range(height_cells):
            for x in range(width_cells):
                cell = self.terrain.get_cell(x, y)
                if cell is not None:
                    dem[y, x] = cell.elevation + type_bump.get(cell.terrain_type, 0.0)

        return dem

    def get_heightmap(self) -> np.ndarray:
        """Return the elevation surface (cached)."""
        key = (
            self.terrain.get_width_cells() if self.terrain else 0,
            self.terrain.get_height_cells() if self.terrain else 0,
        )
        if self._elevation is None or self._cache_key != key:
            self._elevation = self._build_heightmap()
            self._cache_key = key
        return self._elevation

    # ------------------------------------------------------------------
    # Slope & Aspect
    # ------------------------------------------------------------------

    def get_slope(self) -> np.ndarray:
        """Return slope in degrees at every cell."""
        if self._slope is None:
            dem = self.get_heightmap()
            if dem.size == 0:
                self._slope = np.zeros((20, 20), dtype=np.float32)
                return self._slope

            # Gradient along x and y (cell size = 1 unit)
            dz_dx, dz_dy = np.gradient(dem)
            # Slope angle in degrees (vertical exaggeration optional)
            slope_rad = np.arctan(np.sqrt(dz_dx**2 + dz_dy**2))
            self._slope = np.degrees(slope_rad)
        return self._slope

    def get_aspect(self) -> np.ndarray:
        """Return aspect (downhill direction) in degrees compass (0-360)."""
        if self._aspect is None:
            dem = self.get_heightmap()
            if dem.size == 0:
                self._aspect = np.zeros((20, 20), dtype=np.float32)
                return self._aspect

            dz_dx, dz_dy = np.gradient(dem)
            # Aspect = arctan2(-dz_dy, -dz_dx), then convert to compass
            aspect_rad = np.arctan2(-dz_dy, -dz_dx)
            aspect_deg = np.degrees(aspect_rad)
            aspect_deg = (90.0 - aspect_deg) % 360.0  # 0 = North, clockwise
            self._aspect = aspect_deg
        return self._aspect

    # ------------------------------------------------------------------
    # Hillshade / Relief Shading
    # ------------------------------------------------------------------

    def get_hillshade(self, azimuth: float = 315.0, altitude: float = 45.0) -> np.ndarray:
        """Return shaded relief image (0-255).

        Args:
            azimuth: Sun azimuth (compass degrees).
            altitude: Sun altitude (degrees above horizon).
        """
        if self._hillshade is None:
            dem = self.get_heightmap()
            if dem.size == 0:
                self._hillshade = np.full((20, 20), 128, dtype=np.uint8)
                return self._hillshade

            slope = self.get_slope()
            aspect = self.get_aspect()

            az = math.radians(azimuth)
            alt = math.radians(altitude)
            sl = np.radians(slope)
            asp = np.radians(aspect)

            # Standard hillshade formula
            shaded = (
                np.sin(alt) * np.cos(sl)
                + np.cos(alt) * np.sin(sl) * np.cos(az - asp)
            )
            shaded = np.clip(shaded, 0.0, 1.0)
            self._hillshade = (shaded * 255).astype(np.uint8)
        return self._hillshade

    # ------------------------------------------------------------------
    # Viewshed
    # ------------------------------------------------------------------

    def compute_viewshed(
        self,
        observer: Tuple[int, int],
        observer_height: float = 2.0,
        max_range: float = 50.0,
    ) -> Dict[str, Any]:
        """Compute visibility from an observer position.

        Uses Bresenham line sampling between observer and each target cell.
        A target is visible if no intervening cell's effective elevation
        blocks the line (accounting for Earth-curvature-free straight rays).

        Args:
            observer: (x, y) grid coordinates of the observer.
            observer_height: Height of observer above terrain (meters).
            max_range: Maximum viewing distance in grid cells.

        Returns:
            Dict with:
            - visible: (height, width) boolean mask
            - visible_count: number of visible cells
            - total_cells: total cells within range
            - coverage_ratio: visible / total
        """
        dem = self.get_heightmap()
        if dem.size == 0:
            return {"visible": np.zeros((20, 20), dtype=bool), "visible_count": 0,
                    "total_cells": 0, "coverage_ratio": 0.0}

        h, w = dem.shape
        visible = np.zeros((h, w), dtype=bool)

        ox, oy = int(observer[0]), int(observer[1])
        if not (0 <= ox < w and 0 <= oy < h):
            return {"visible": visible, "visible_count": 0,
                    "total_cells": 0, "coverage_ratio": 0.0}

        obs_elev = dem[oy, ox] + observer_height
        total_in_range = 0

        for ty in range(h):
            for tx in range(w):
                dx = tx - ox
                dy = ty - oy
                dist = math.hypot(dx, dy)
                if dist > max_range:
                    continue
                if dist == 0:
                    visible[ty, tx] = True
                    total_in_range += 1
                    continue

                total_in_range += 1
                steps = max(2, int(dist * 2))
                visible_flag = True
                for i in range(1, steps):
                    t = i / steps
                    sx = int(round(ox + t * dx))
                    sy = int(round(oy + t * dy))
                    if not (0 <= sx < w and 0 <= sy < h):
                        continue
                    cell_elev = dem[sy, sx]
                    # Linear ray elevation at this point
                    ray_elev = obs_elev - (obs_elev - dem[ty, tx]) * (t * dist) / dist
                    # If the terrain rises above the ray, the target is blocked
                    if cell_elev >= ray_elev:
                        visible_flag = False
                        break
                visible[ty, tx] = visible_flag

        visible_count = int(visible.sum())
        return {
            "visible": visible,
            "visible_count": visible_count,
            "total_cells": total_in_range,
            "coverage_ratio": visible_count / max(1, total_in_range),
        }

    # ------------------------------------------------------------------
    # Terrain classification helpers
    # ------------------------------------------------------------------

    def get_dominant_terrain(self) -> Dict[str, int]:
        """Count terrain type distribution across the grid."""
        if self.terrain is None:
            return {}
        counts: Dict[str, int] = {}
        for x in range(self.terrain.get_width_cells()):
            for y in range(self.terrain.get_height_cells()):
                cell = self.terrain.get_cell(x, y)
                if cell is not None:
                    key = cell.terrain_type.value
                    counts[key] = counts.get(key, 0) + 1
        return counts

    def get_average_elevation(self) -> float:
        """Average elevation across the battlefield."""
        dem = self.get_heightmap()
        if dem.size == 0:
            return 0.0
        return float(dem.mean())

    def get_max_elevation(self) -> float:
        """Maximum elevation across the battlefield."""
        dem = self.get_heightmap()
        if dem.size == 0:
            return 0.0
        return float(dem.max())

    def get_elevation_at(self, x: int, y: int) -> float:
        """Get elevation at a specific grid cell."""
        dem = self.get_heightmap()
        if dem.size == 0:
            return 0.0
        h, w = dem.shape
        if 0 <= y < h and 0 <= x < w:
            return float(dem[y, x])
        return 0.0

    def export_scene(self) -> Dict[str, Any]:
        """Export the 3D terrain model as a JSON-serializable scene dict.

        This is consumed by the frontend Three.js ``Terrain3DMap`` component.
        """
        dem = self.get_heightmap()
        slope = self.get_slope()
        aspect = self.get_aspect()
        hillshade = self.get_hillshade()

        return {
            "width": int(dem.shape[1]) if dem.size else 0,
            "height": int(dem.shape[0]) if dem.size else 0,
            "heightmap": dem.astype(float).tolist(),
            "slope": slope.astype(float).tolist(),
            "aspect": aspect.astype(float).tolist(),
            "hillshade": hillshade.tolist(),
            "stats": {
                "min_elevation": float(dem.min()) if dem.size else 0.0,
                "max_elevation": float(dem.max()) if dem.size else 0.0,
                "avg_elevation": self.get_average_elevation(),
                "dominant_terrain": self.get_dominant_terrain(),
            },
        }

    def get_stats(self) -> Dict[str, Any]:
        """Return analysis statistics."""
        return {
            "grid_size": f"{self.get_heightmap().shape[1]}x{self.get_heightmap().shape[0]}",
            "avg_elevation": self.get_average_elevation(),
            "max_elevation": self.get_max_elevation(),
            "dominant_terrain": self.get_dominant_terrain(),
        }

