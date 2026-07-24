"""Dynamic terrain model with elevation, cover, and trafficability."""

from __future__ import annotations

import logging
import numpy as np
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from .base import WorldModel, WorldModelConfig

logger = logging.getLogger("Ultrone.Sim.WorldModeling.Terrain")


@dataclass
class TerrainConfig(WorldModelConfig):
    """Configuration for terrain model."""
    width: int = 100
    height: int = 100
    num_elevation_levels: int = 5
    num_cover_types: int = 3  # open, partial, full


class TerrainModel(WorldModel):
    """Dynamic terrain model.

    Features:
    - Elevation map with multiple levels
    - Cover type classification (open/partial/full)
    - Trafficability (cost) map
    - Dynamic terrain changes (e.g., craters from explosions)
    """

    def __init__(self, config: Optional[TerrainConfig] = None):
        super().__init__(config or TerrainConfig())
        self._elevation: np.ndarray = np.zeros((config.height, config.width))
        self._cover: np.ndarray = np.zeros((config.height, config.width), dtype=int)
        self._trafficability: np.ndarray = np.ones((config.height, config.width))

    def initialize(self, seed: Optional[int] = None) -> None:
        """Generate initial terrain using procedural generation."""
        rng = np.random.RandomState(seed or self.config.seed)
        h, w = self.config.height, self.config.width

        # Perlin-like simple elevation generation
        x = np.linspace(0, 4 * np.pi, w)
        y = np.linspace(0, 4 * np.pi, h)
        xx, yy = np.meshgrid(x, y)
        self._elevation = (np.sin(xx) * np.cos(yy) + 1) / 2 * self.config.num_elevation_levels
        self._elevation = np.round(self._elevation).astype(float)

        # Cover types based on elevation
        self._cover = np.zeros_like(self._elevation, dtype=int)
        self._cover[self._elevation > 2] = 1  # partial cover
        self._cover[self._elevation > 4] = 2  # full cover

        # Trafficability: higher elevation = harder to traverse
        self._trafficability = 1.0 + 0.2 * self._elevation

        logger.info("Terrain initialized: %dx%d, %d elevation levels", w, h, self.config.num_elevation_levels)

    def update(self, dt: float) -> None:
        """Terrain changes slowly over time (erosion simulation)."""
        self._tick += 1

    def modify_terrain(self, x: int, y: int, radius: int, crater_depth: float = 1.0) -> None:
        """Create a crater at (x, y) with given radius."""
        h, w = self.config.height, self.config.width
        for dy in range(-radius, radius + 1):
            for dx in range(-radius, radius + 1):
                nx, ny = x + dx, y + dy
                if 0 <= nx < w and 0 <= ny < h:
                    dist = np.sqrt(dx**2 + dy**2)
                    if dist <= radius:
                        self._elevation[ny, nx] = max(0, self._elevation[ny, nx] - crater_depth * (1 - dist / radius))
                        self._trafficability[ny, nx] = min(5.0, self._trafficability[ny, nx] + 0.5 * (1 - dist / radius))

    def get_elevation(self, x: int, y: int) -> float:
        return float(self._elevation[y, x])

    def get_cover(self, x: int, y: int) -> int:
        return int(self._cover[y, x])

    def get_trafficability(self, x: int, y: int) -> float:
        return float(self._trafficability[y, x])

    def get_state(self) -> Dict[str, Any]:
        return {
            "elevation": self._elevation.tolist(),
            "cover": self._cover.tolist(),
            "trafficability": self._trafficability.tolist(),
        }

    def reset(self) -> None:
        super().reset()
        self.initialize()

