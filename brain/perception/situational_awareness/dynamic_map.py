# Copyright (c) Ultrone Contributors. All rights reserved.
"""Dynamic map of the environment.

Maintains a continuously updated spatial map with occupancy, terrain, and
dynamic entity layers. Supports grid-based occupancy, spatial queries, and
map evolution over time.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from .types import EntityCategory, TrackedEntity, Vector3, utc_now

__all__ = [
    "MapCell",
    "DynamicMap",
    "DynamicMapConfig",
]


@dataclass
class MapCell:
    """A cell in the dynamic map grid."""

    x: int
    y: int
    z: int = 0
    occupancy: float = 0.0
    confidence: float = 0.0
    label: str = "unknown"
    category: Optional[EntityCategory] = None
    last_updated: datetime = field(default_factory=utc_now)
    attributes: Dict[str, Any] = field(default_factory=dict)


class DynamicMapConfig:
    """Configuration for the dynamic map."""

    def __init__(
        self,
        *,
        resolution: float = 1.0,
        width: int = 100,
        height: int = 100,
        depth: int = 1,
        occupancy_decay: float = 0.01,
    ) -> None:
        self.resolution = resolution
        self.width = width
        self.height = height
        self.depth = depth
        self.occupancy_decay = occupancy_decay


class DynamicMap:
    """Grid-based dynamic map with occupancy and semantic layers."""

    def __init__(self, *, config: Optional[DynamicMapConfig] = None) -> None:
        self._config = config or DynamicMapConfig()
        self._cells: Dict[Tuple[int, int, int], MapCell] = {}
        self._origin = Vector3()

    def set_origin(self, origin: Vector3) -> None:
        self._origin = origin

    def world_to_grid(self, position: Vector3) -> Tuple[int, int, int]:
        """Convert a world position to grid coordinates."""
        x = int((position.x - self._origin.x) / self._config.resolution)
        y = int((position.y - self._origin.y) / self._config.resolution)
        z = int((position.z - self._origin.z) / self._config.resolution)
        return x, y, z

    def grid_to_world(self, x: int, y: int, z: int = 0) -> Vector3:
        """Convert grid coordinates to a world position (cell center)."""
        return Vector3(
            x=self._origin.x + (x + 0.5) * self._config.resolution,
            y=self._origin.y + (y + 0.5) * self._config.resolution,
            z=self._origin.z + (z + 0.5) * self._config.resolution,
        )

    def get_cell(self, x: int, y: int, z: int = 0) -> Optional[MapCell]:
        return self._cells.get((x, y, z))

    def get_cell_at(self, position: Vector3) -> Optional[MapCell]:
        x, y, z = self.world_to_grid(position)
        return self.get_cell(x, y, z)

    def update_occupancy(
        self,
        position: Vector3,
        occupancy: float,
        *,
        confidence: float = 0.5,
        label: str = "occupied",
        category: Optional[EntityCategory] = None,
    ) -> MapCell:
        """Update the occupancy of the cell at the given position."""
        x, y, z = self.world_to_grid(position)
        key = (x, y, z)
        cell = self._cells.get(key)
        if cell is None:
            cell = MapCell(x=x, y=y, z=z)
            self._cells[key] = cell

        # Exponential moving average for occupancy.
        alpha = 0.3
        if cell.occupancy == 0.0:
            cell.occupancy = occupancy
        else:
            cell.occupancy = alpha * occupancy + (1 - alpha) * cell.occupancy
        cell.confidence = max(cell.confidence, confidence)
        cell.label = label
        cell.category = category
        cell.last_updated = utc_now()
        return cell

    def update_entity(self, entity: TrackedEntity) -> Optional[MapCell]:
        """Update the map based on an entity's position."""
        return self.update_occupancy(
            entity.state.position,
            occupancy=1.0,
            confidence=entity.confidence,
            label=entity.entity_type.value,
            category=entity.category,
        )

    def is_occupied(self, position: Vector3, threshold: float = 0.5) -> bool:
        cell = self.get_cell_at(position)
        return cell is not None and cell.occupancy >= threshold

    def occupancy_at(self, position: Vector3) -> float:
        cell = self.get_cell_at(position)
        return cell.occupancy if cell else 0.0

    def label_at(self, position: Vector3) -> str:
        cell = self.get_cell_at(position)
        return cell.label if cell else "unknown"

    def occupied_cells(self, threshold: float = 0.5) -> List[MapCell]:
        return [c for c in self._cells.values() if c.occupancy >= threshold]

    def free_cells(self, threshold: float = 0.2) -> List[MapCell]:
        return [c for c in self._cells.values() if c.occupancy <= threshold]

    def decay(self, rate: Optional[float] = None) -> None:
        """Decay occupancy values over time."""
        rate = rate or self._config.occupancy_decay
        for cell in self._cells.values():
            cell.occupancy = max(0.0, cell.occupancy - rate)

    def clear(self) -> None:
        self._cells.clear()

    def cell_count(self) -> int:
        return len(self._cells)

    def to_occupancy_grid(self) -> np.ndarray:
        """Export the map as a 2D occupancy grid array."""
        grid = np.zeros((self._config.height, self._config.width), dtype=np.float64)
        for (x, y, z), cell in self._cells.items():
            if 0 <= x < self._config.width and 0 <= y < self._config.height:
                grid[y, x] = cell.occupancy
        return grid