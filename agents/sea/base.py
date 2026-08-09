# Copyright (c) Ultrone Contributors. All rights reserved.
"""Base class for sea domain agents."""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Tuple

from agents.base_agent import BaseAgent, AgentCapability
from agents.config import SeaAgentConfig
from data.entities import DomainType, Contact

logger = logging.getLogger("Ultrone.Agents.Sea.Base")


class SeaAgent(BaseAgent):
    """
    Base class for all sea domain agents.
    
    Provides common sea-domain functionality:
    - Depth management (for submarines)
    - Position and movement management
    - Fuel/energy consumption
    - Sensor range management
    - Environmental constraints
    """
    
    def __init__(
        self,
        unit_id: str,
        position: Tuple[float, float, float],
        team: str = "blue",
        config: Optional[SeaAgentConfig] = None,
        **kwargs,
    ):
        """
        Initialize sea agent.
        
        Args:
            unit_id: Unique identifier
            position: (x, y, z) where z is depth (negative for below surface)
            team: Team affiliation
            config: Sea-specific configuration
        """
        super().__init__(
            unit_id=unit_id,
            domain=DomainType.SEA,
            unit_type=self._get_unit_type(),
            position=position,
            team=team,
            capabilities=self._get_capabilities(),
            **kwargs,
        )
        
        # Sea-specific configuration
        self.config = config or SeaAgentConfig(
            agent_id=unit_id,
            team=team,
            domain=DomainType.SEA,
        )
        
        # Sea-specific state
        self.depth: float = abs(position[2]) if len(position) > 2 else 0.0  # meters below surface
        self.target_depth: float = 0.0
        self.heading: float = 0.0  # degrees
        self.speed: float = 0.0
        self.max_speed: float = self.config.max_speed
        self.max_depth: float = self.config.max_depth
        self.fuel: float = self.config.max_fuel
        
        # Movement state
        self.movement_state: str = "idle"  # idle, moving, submerged, surfaced
        self.target_position: Optional[Tuple[float, float, float]] = None
        self.waypoints: List[Tuple[float, float, float]] = []
        self.current_waypoint_index: int = 0
        
        # Combat state
        self.stealth_mode: bool = False
        self.sonar_active: bool = True
        self.radar_active: bool = True
        self.target_contact: Optional[Contact] = None
    
    def _get_unit_type(self) -> str:
        """Return the unit type string. Override in subclasses."""
        return "sea_generic"
    
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
    
    def set_depth(self, depth: float) -> None:
        """
        Set target depth.
        
        Args:
            depth: Depth in meters (positive = below surface)
        """
        self.target_depth = max(0.0, min(depth, self.max_depth))
    
    def surface(self) -> None:
        """Surface the vessel."""
        self.target_depth = 0.0
        self.movement_state = "surfaced"
    
    def submerge(self, depth: Optional[float] = None) -> None:
        """
        Submerge the vessel.
        
        Args:
            depth: Target depth in meters (defaults to 50% of max_depth)
        """
        target = depth if depth is not None else self.max_depth * 0.5
        self.set_depth(target)
        self.movement_state = "submerged"
    
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
        self.movement_state = "idle"
    
    def enable_stealth(self) -> None:
        """Enable stealth mode (reduce emissions)."""
        self.stealth_mode = True
        self.sonar_active = False
        self.radar_active = False
    
    def disable_stealth(self) -> None:
        """Disable stealth mode."""
        self.stealth_mode = False
        self.sonar_active = True
        self.radar_active = True
    
    def update(self, world_state: Any, delta_time: float = 1.0) -> None:
        """
        Update sea agent state.
        
        Handles:
        - Depth changes
        - Movement towards target
        - Fuel consumption
        - Sensor updates
        """
        # Consume fuel based on movement
        if self.movement_state in ["moving", "submerged"]:
            fuel_consumption = 0.008 * delta_time
            if not self.consume_fuel(fuel_consumption):
                self.stop()
                logger.warning(f"{self.unit.unit_id} out of fuel, stopped")
        
        # Update depth if changing
        if self.movement_state == "submerged" and abs(self.depth - self.target_depth) > 0.1:
            depth_rate = 2.0  # meters per second
            if self.depth < self.target_depth:
                self.depth = min(self.target_depth, self.depth + depth_rate * delta_time)
            else:
                self.depth = max(self.target_depth, self.depth - depth_rate * delta_time)
            self.unit.position = (
                self.unit.position[0],
                self.unit.position[1],
                -self.depth,  # Negative z for below surface
            )
        
        # Update position if moving
        if self.movement_state == "moving" and self.target_position:
            dx = self.target_position[0] - self.unit.position[0]
            dy = self.target_position[1] - self.unit.position[1]
            distance = (dx**2 + dy**2) ** 0.5
            
            if distance < 1.0:
                self.unit.position = self.target_position
                self.stop()
            else:
                move_amount = min(self.speed * delta_time, distance)
                new_x = self.unit.position[0] + (dx / distance) * move_amount
                new_y = self.unit.position[1] + (dy / distance) * move_amount
                self.unit.position = (new_x, new_y, self.unit.position[2])
    
    def get_stats(self) -> dict:
        """Get sea agent statistics."""
        stats = super().get_stats() if hasattr(super(), "get_stats") else {}
        stats.update({
            "depth": self.depth,
            "target_depth": self.target_depth,
            "heading": self.heading,
            "speed": self.speed,
            "max_depth": self.max_depth,
            "max_speed": self.max_speed,
            "movement_state": self.movement_state,
            "stealth_mode": self.stealth_mode,
            "sonar_active": self.sonar_active,
            "radar_active": self.radar_active,
        })
        return stats
    
    def to_dict(self) -> dict:
        """Serialize agent state."""
        data = super().to_dict()
        data.update({
            "depth": self.depth,
            "target_depth": self.target_depth,
            "heading": self.heading,
            "speed": self.speed,
            "max_speed": self.max_speed,
            "max_depth": self.max_depth,
            "movement_state": self.movement_state,
            "target_position": self.target_position,
            "waypoints": self.waypoints,
            "current_waypoint_index": self.current_waypoint_index,
            "stealth_mode": self.stealth_mode,
            "sonar_active": self.sonar_active,
            "radar_active": self.radar_active,
        })
        return data
    
    def from_dict(self, data: dict) -> None:
        """Deserialize agent state."""
        super().from_dict(data)
        self.depth = data.get("depth", self.depth)
        self.target_depth = data.get("target_depth", self.target_depth)
        self.heading = data.get("heading", self.heading)
        self.speed = data.get("speed", self.speed)
        self.max_speed = data.get("max_speed", self.max_speed)
        self.max_depth = data.get("max_depth", self.max_depth)
        self.movement_state = data.get("movement_state", self.movement_state)
        self.target_position = data.get("target_position", None)
        self.waypoints = data.get("waypoints", [])
        self.current_waypoint_index = data.get("current_waypoint_index", 0)
        self.stealth_mode = data.get("stealth_mode", False)
        self.sonar_active = data.get("sonar_active", True)
        self.radar_active = data.get("radar_active", True)