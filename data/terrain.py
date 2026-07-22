# Copyright (c) Ultrone Contributors. All rights reserved.
"""Terrain and line-of-sight models for battlefield simulation."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Tuple, Optional, Dict


class TerrainType(Enum):
    """Terrain types affecting movement and visibility."""
    OPEN = "open"           # No obstruction
    PLAINS = "plains"       # Light vegetation, open sight lines
    FOREST = "forest"       # Heavy vegetation, reduced visibility
    URBAN = "urban"         # Buildings, significant obstruction
    MOUNTAIN = "mountain"   # High elevation, rocky
    HILLS = "hills"         # Rolling terrain, moderate obstruction
    DESERT = "desert"       # Open with occasional dunes
    WATER = "water"         # Ocean, sea
    COASTAL = "coastal"     # Water meets land
    SUBMERGED = "submerged" # Underwater


@dataclass
class GridCell:
    """A single cell in the terrain grid."""
    x: int
    y: int
    terrain_type: TerrainType = TerrainType.OPEN
    elevation: float = 0.0  # meters above sea level
    is_occupied: bool = False
    occupied_by: Optional[str] = None  # unit_id if occupied
    
    def get_movement_cost(self) -> float:
        """Get movement penalty for this terrain type."""
        costs = {
            TerrainType.OPEN: 1.0,
            TerrainType.PLAINS: 1.1,
            TerrainType.FOREST: 2.0,
            TerrainType.URBAN: 3.0,
            TerrainType.MOUNTAIN: 5.0,
            TerrainType.HILLS: 1.5,
            TerrainType.DESERT: 1.2,
            TerrainType.WATER: 10.0,  # Requires watercraft
            TerrainType.COASTAL: 1.3,
            TerrainType.SUBMERGED: 8.0,  # Requires submarine
        }
        return costs.get(self.terrain_type, 1.0)
    
    def blocks_line_of_sight(self) -> bool:
        """Check if terrain blocks optical LOS."""
        return self.terrain_type in (TerrainType.FOREST, TerrainType.URBAN, TerrainType.MOUNTAIN)


class LineOfSight:
    """Calculates line of sight between two points."""
    
    @staticmethod
    def check_los(
        start: Tuple[float, float, float],
        end: Tuple[float, float, float],
        terrain_grid: Optional['Terrain'] = None,
        weather_factor: float = 1.0
    ) -> Tuple[bool, float]:
        """
        Check if line of sight exists between two 3D points.
        
        Returns: (has_los, max_elevation_angle)
        """
        distance = ((end[0] - start[0]) ** 2 + 
                   (end[1] - start[1]) ** 2 + 
                   (end[2] - start[2]) ** 2) ** 0.5
        
        if distance == 0:
            return True, 0.0
        
        max_elevation = 0.0
        
        if terrain_grid:
            # Sample terrain along the path
            steps = int(distance / 100) + 1  # Sample every 100m
            for i in range(1, steps):
                t = i / steps
                sample_x = int(start[0] + t * (end[0] - start[0]))
                sample_y = int(start[1] + t * (end[1] - start[1]))
                cell = terrain_grid.get_cell(sample_x, sample_y)
                if cell and cell.blocks_line_of_sight():
                    # Check if terrain elevation blocks LOS
                    target_elevation = max(0, end[2] - start[2])
                    if cell.elevation > target_elevation:
                        return False, cell.elevation
        
        # Weather affects visibility
        effective_weather = min(1.0, weather_factor)
        has_los = effective_weather > 0.3  # Below 30% visibility, LOS is degraded
        
        return has_los, max_elevation


@dataclass
class Terrain:
    """The operational terrain for simulation."""
    width_meters: int
    height_meters: int
    cell_size_meters: int = 100  # Each grid cell represents this many meters
    cells: Dict[Tuple[int, int], GridCell] = field(default_factory=dict)
    
    def __post_init__(self):
        """Initialize grid if not provided."""
        if not self.cells:
            width_cells = self.width_meters // self.cell_size_meters
            height_cells = self.height_meters // self.cell_size_meters
            for x in range(width_cells):
                for y in range(height_cells):
                    self.cells[(x, y)] = GridCell(x=x, y=y, terrain_type=TerrainType.OPEN, elevation=0.0)
    
    def get_cell(self, x: int, y: int) -> Optional[GridCell]:
        """Get a cell by grid coordinates."""
        return self.cells.get((x, y))
    
    def get_cell_meters(self, meters_x: float, meters_y: float) -> Optional[GridCell]:
        """Get a cell by meter coordinates."""
        grid_x = int(meters_x // self.cell_size_meters)
        grid_y = int(meters_y // self.cell_size_meters)
        return self.get_cell(grid_x, grid_y)
    
    def set_terrain(self, x: int, y: int, terrain_type: TerrainType, elevation: float = 0.0) -> None:
        """Set terrain type for a cell."""
        if (x, y) in self.cells:
            self.cells[(x, y)].terrain_type = terrain_type
            self.cells[(x, y)].elevation = elevation
    
    def is_water(self, x: int, y: int) -> bool:
        """Check if a cell is water."""
        cell = self.get_cell(x, y)
        return cell is not None and cell.terrain_type in (TerrainType.WATER, TerrainType.COASTAL)
    
    def get_width_cells(self) -> int:
        """Get terrain width in cells."""
        return self.width_meters // self.cell_size_meters
    
    def get_height_cells(self) -> int:
        """Get terrain height in cells."""
        return self.height_meters // self.cell_size_meters