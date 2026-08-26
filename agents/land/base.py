# Copyright (c) Ultrone Contributors. All rights reserved.
"""Base class for land domain agents."""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Tuple

from agents.base_agent import BaseAgent, AgentCapability
from agents.platform_agent import SubsystemControlledAgent
from agents.config import LandAgentConfig
from data.entities import DomainType, Contact

logger = logging.getLogger("Ultrone.Agents.Land.Base")


class LandAgent(SubsystemControlledAgent):
    """
    Base class for all land domain agents.
    
    Provides common land-domain functionality:
    - Position and movement management
    - Terrain compatibility checking
    - Fuel/energy consumption
    - Sensor range management
    """
    
    def __init__(
        self,
        unit_id: str,
        position: Tuple[float, float, float],
        team: str = "blue",
        config: Optional[LandAgentConfig] = None,
        **kwargs,
    ):
        """
        Initialize land agent.
        
        Args:
            unit_id: Unique identifier
            position: (x, y, z) where z is elevation
            team: Team affiliation
            config: Land-specific configuration
        """
        super().__init__(
            unit_id=unit_id,
            domain=DomainType.LAND,
            unit_type=self._get_unit_type(),
            position=position,
            team=team,
            capabilities=self._get_capabilities(),
            **kwargs,
        )
        
        # Land-specific configuration
        self.config = config or LandAgentConfig(
            agent_id=unit_id,
            team=team,
            domain=DomainType.LAND,
        )
        
        # Land-specific state
        self.heading: float = 0.0  # degrees
        self.speed: float = 0.0
        self.max_speed: float = self.config.max_speed
        self.terrain_compatibility: List[str] = list(self.config.terrain_compatibility)
        self.armor_rating: float = self.config.armor_rating
        self.weapon_range: float = self.config.weapon_range
        
        # Movement state
        self.movement_state: str = "idle"  # idle, moving, stopped, hull_down
        self.target_position: Optional[Tuple[float, float, float]] = None
        self.path: List[Tuple[float, float, float]] = []
        self.current_path_index: int = 0
        
        # Combat state
        self.cover_available: bool = False
        self.concealment: float = 0.0  # 0.0-1.0
        self.target_contact: Optional[Contact] = None
    
    def _get_unit_type(self) -> str:
        """Return the unit type string. Override in subclasses."""
        return "land_generic"
    
    def _get_capabilities(self) -> List[AgentCapability]:
        """Return default capabilities. Override in subclasses."""
        return [
            AgentCapability.SENSE,
            AgentCapability.MOVE,
            AgentCapability.ENGAGE,
        ]
    
    def set_heading(self, heading: float) -> None:
        """Set heading in degrees (0-360)."""
        self.heading = heading % 360.0
    
    def move_to(self, target: Tuple[float, float, float], speed: Optional[float] = None) -> None:
        """
        Set movement target.
        
        Args:
            target: (x, y, z) target position
            speed: Movement speed (defaults to max_speed)
        """
        self.target_position = target
        self.speed = speed or self.max_speed
        self.movement_state = "moving"
    
    def stop(self) -> None:
        """Stop movement."""
        self.target_position = None
        self.speed = 0.0
        self.movement_state = "stopped"
    
    def take_hull_down(self) -> None:
        """Take hull-down position (behind cover)."""
        self.movement_state = "hull_down"
        self.speed = 0.0
        self.cover_available = True
    
    def check_terrain_compatibility(self, terrain_type: str) -> bool:
        """
        Check if agent can operate on given terrain.
        
        Args:
            terrain_type: Type of terrain (e.g., "road", "dirt", "water")
        """
        return terrain_type in self.terrain_compatibility
    
    def update(self, world_state: Any, delta_time: float = 1.0) -> None:
        """
        Update land agent state.
        
        Handles:
        - Movement towards target
        - Terrain effects
        - Fuel/energy consumption
        - Sensor updates
        """
        # Consume fuel based on movement
        if self.movement_state == "moving":
            fuel_consumption = 0.005 * delta_time
            if not self.consume_fuel(fuel_consumption):
                self.stop()
                logger.warning(f"{self.unit.unit_id} out of fuel, stopped")
        
        # Update position if moving
        if self.movement_state == "moving" and self.target_position:
            # Simple linear movement (real implementation would use pathfinding)
            dx = self.target_position[0] - self.unit.position[0]
            dy = self.target_position[1] - self.unit.position[1]
            distance = (dx**2 + dy**2) ** 0.5
            
            if distance < 1.0:
                # Reached target
                self.unit.position = self.target_position
                self.stop()
            else:
                # Move towards target
                move_amount = min(self.speed * delta_time, distance)
                new_x = self.unit.position[0] + (dx / distance) * move_amount
                new_y = self.unit.position[1] + (dy / distance) * move_amount
                self.unit.position = (new_x, new_y, self.unit.position[2])
    
    def get_stats(self) -> dict:
        """Get land agent statistics."""
        stats = super().get_stats() if hasattr(super(), "get_stats") else {}
        stats.update({
            "heading": self.heading,
            "speed": self.speed,
            "movement_state": self.movement_state,
            "terrain_compatibility": self.terrain_compatibility,
            "armor_rating": self.armor_rating,
            "weapon_range": self.weapon_range,
            "cover_available": self.cover_available,
            "concealment": self.concealment,
        })
        return stats
    
    def to_dict(self) -> dict:
        """Serialize agent state."""
        data = super().to_dict()
        data.update({
            "heading": self.heading,
            "speed": self.speed,
            "max_speed": self.max_speed,
            "terrain_compatibility": self.terrain_compatibility,
            "armor_rating": self.armor_rating,
            "weapon_range": self.weapon_range,
            "movement_state": self.movement_state,
            "target_position": self.target_position,
            "path": self.path,
            "current_path_index": self.current_path_index,
            "cover_available": self.cover_available,
            "concealment": self.concealment,
        })
        return data
    
    def from_dict(self, data: dict) -> None:
        """Deserialize agent state."""
        super().from_dict(data)
        self.heading = data.get("heading", self.heading)
        self.speed = data.get("speed", self.speed)
        self.max_speed = data.get("max_speed", self.max_speed)
        self.terrain_compatibility = data.get("terrain_compatibility", self.terrain_compatibility)
        self.armor_rating = data.get("armor_rating", self.armor_rating)
        self.weapon_range = data.get("weapon_range", self.weapon_range)
        self.movement_state = data.get("movement_state", self.movement_state)
        self.target_position = data.get("target_position", None)
        self.path = data.get("path", [])
        self.current_path_index = data.get("current_path_index", 0)
        self.cover_available = data.get("cover_available", False)
        self.concealment = data.get("concealment", 0.0)