# Copyright (c) Ultrone Contributors. All rights reserved.
"""Base class for air domain agents."""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Tuple

from agents.base_agent import BaseAgent, AgentCapability
from agents.config import AirAgentConfig
from data.entities import DomainType, Contact

logger = logging.getLogger("Ultrone.Agents.Air.Base")


class AirAgent(BaseAgent):
    """
    Base class for all air domain agents.
    
    Provides common air-domain functionality:
    - Altitude management
    - Fuel consumption
    - Sensor range at altitude
    - Air-to-air and air-to-ground modes
    """
    
    def __init__(
        self,
        unit_id: str,
        position: Tuple[float, float, float],
        team: str = "blue",
        config: Optional[AirAgentConfig] = None,
        **kwargs,
    ):
        """
        Initialize air agent.
        
        Args:
            unit_id: Unique identifier
            position: (x, y, z) where z is altitude in meters
            team: Team affiliation
            config: Air-specific configuration
        """
        super().__init__(
            unit_id=unit_id,
            domain=DomainType.AIR,
            unit_type=self._get_unit_type(),
            position=position,
            team=team,
            capabilities=self._get_capabilities(),
            **kwargs,
        )
        
        # Air-specific configuration
        self.config = config or AirAgentConfig(
            agent_id=unit_id,
            team=team,
            domain=DomainType.AIR,
        )
        
        # Air-specific state
        self.altitude: float = position[2] if len(position) > 2 else 0.0
        self.target_altitude: float = self.config.cruise_altitude
        self.heading: float = 0.0  # degrees
        self.speed: float = 0.0
        self.fuel: float = self.config.max_fuel
        self.max_altitude: float = self.config.max_altitude
        self.max_speed: float = self.config.max_speed
        
        # Mission state
        self.mission_phase: str = "idle"  # idle, climb, cruise, descent, loiter, engage, rtb
        self.target_contact: Optional[Contact] = None
        self.waypoints: List[Tuple[float, float, float]] = []
        self.current_waypoint_index: int = 0
    
    def _get_unit_type(self) -> str:
        """Return the unit type string. Override in subclasses."""
        return "air_generic"
    
    def _get_capabilities(self) -> List[AgentCapability]:
        """Return default capabilities. Override in subclasses."""
        return [
            AgentCapability.SENSE,
            AgentCapability.MOVE,
            AgentCapability.ENGAGE,
        ]
    
    def set_altitude(self, altitude: float) -> None:
        """Set target altitude (climb/descent handled in update)."""
        self.target_altitude = max(0.0, min(altitude, self.max_altitude))
    
    def climb(self, rate: float = 10.0) -> None:
        """Climb to target altitude."""
        if self.altitude < self.target_altitude:
            self.altitude = min(self.target_altitude, self.altitude + rate)
            self.unit.position = (
                self.unit.position[0],
                self.unit.position[1],
                self.altitude,
            )
    
    def descend(self, rate: float = 10.0) -> None:
        """Descend to target altitude."""
        if self.altitude > self.target_altitude:
            self.altitude = max(self.target_altitude, self.altitude - rate)
            self.unit.position = (
                self.unit.position[0],
                self.unit.position[1],
                self.altitude,
            )
    
    def consume_fuel(self, amount: float) -> bool:
        """
        Consume fuel. Returns True if fuel available.
        
        Args:
            amount: Amount of fuel to consume (0.0-1.0)
        """
        if self.fuel >= amount:
            self.fuel = max(0.0, self.fuel - amount)
            return True
        return False
    
    def update(self, world_state: Any, delta_time: float = 1.0) -> None:
        """
        Update air agent state.
        
        Handles:
        - Altitude changes
        - Fuel consumption
        - Movement towards waypoints
        - Sensor updates
        """
        # Consume fuel based on activity
        if self.mission_phase in ["climb", "cruise"]:
            self.consume_fuel(self.config.fuel_consumption_rate * delta_time)
        
        # Check fuel status
        if self.fuel <= 0.0:
            self.mission_phase = "rtb"
            logger.warning(f"{self.unit.unit_id} out of fuel, returning to base")
        
        # Update sensor range based on altitude
        if self.altitude > 0:
            altitude_factor = min(2.0, 1.0 + (self.altitude / self.config.max_altitude))
            self.unit.sensor_range = self.config.sensor_range * altitude_factor
    
    def get_stats(self) -> dict:
        """Get air agent statistics."""
        stats = super().get_stats() if hasattr(super(), "get_stats") else {}
        stats.update({
            "altitude": self.altitude,
            "target_altitude": self.target_altitude,
            "heading": self.heading,
            "speed": self.speed,
            "fuel": self.fuel,
            "mission_phase": self.mission_phase,
            "max_altitude": self.max_altitude,
            "max_speed": self.max_speed,
        })
        return stats
    
    def to_dict(self) -> dict:
        """Serialize agent state."""
        data = super().to_dict()
        data.update({
            "altitude": self.altitude,
            "target_altitude": self.target_altitude,
            "heading": self.heading,
            "speed": self.speed,
            "fuel": self.fuel,
            "mission_phase": self.mission_phase,
            "waypoints": self.waypoints,
            "current_waypoint_index": self.current_waypoint_index,
        })
        return data
    
    def from_dict(self, data: dict) -> None:
        """Deserialize agent state."""
        super().from_dict(data)
        self.altitude = data.get("altitude", self.altitude)
        self.target_altitude = data.get("target_altitude", self.target_altitude)
        self.heading = data.get("heading", self.heading)
        self.speed = data.get("speed", self.speed)
        self.fuel = data.get("fuel", self.fuel)
        self.mission_phase = data.get("mission_phase", self.mission_phase)
        self.waypoints = data.get("waypoints", [])
        self.current_waypoint_index = data.get("current_waypoint_index", 0)