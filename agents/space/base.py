# Copyright (c) Ultrone Contributors. All rights reserved.
"""Base class for space domain agents."""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Tuple

from agents.base_agent import BaseAgent, AgentCapability
from agents.platform_agent import SubsystemControlledAgent
from agents.config import SpaceAgentConfig
from data.entities import DomainType, Contact

logger = logging.getLogger("Ultrone.Agents.Space.Base")


class SpaceAgent(SubsystemControlledAgent):
    """
    Base class for all space domain agents.
    
    Provides common space-domain functionality:
    - Orbital state management
    - Position and velocity management
    - Power/energy management
    - Communication delay simulation
    - Sensor management
    """
    
    def __init__(
        self,
        unit_id: str,
        position: Tuple[float, float, float],
        team: str = "blue",
        config: Optional[SpaceAgentConfig] = None,
        **kwargs,
    ):
        """
        Initialize space agent.
        
        Args:
            unit_id: Unique identifier
            position: (x, y, z) in km (ECI or similar frame)
            team: Team affiliation
            config: Space-specific configuration
        """
        super().__init__(
            unit_id=unit_id,
            domain=DomainType.SPACE,
            unit_type=self._get_unit_type(),
            position=position,
            team=team,
            capabilities=self._get_capabilities(),
            **kwargs,
        )
        
        # Space-specific configuration
        self.config = config or SpaceAgentConfig(
            agent_id=unit_id,
            team=team,
            domain=DomainType.SPACE,
        )
        
        # Space-specific state
        self.orbital_altitude_km: float = self.config.orbital_altitude_km
        self.velocity: Tuple[float, float, float] = (0.0, 0.0, 0.0)
        self.delta_v_remaining: float = self.config.delta_v_capacity
        self.power_level: float = self.config.power_capacity
        self.communication_delay_ms: float = self.config.communication_delay_ms
        
        # Orbit state
        self.orbit_type: str = "LEO"  # LEO, MEO, GEO, HEO
        self.orbital_period_minutes: float = 90.0  # LEO default
        self.inclination_deg: float = 0.0
        
        # Sensor state
        self.sensor_swath_km: float = self.config.sensor_swath_km
        self.sensor_active: bool = True
        
        # Mission state
        self.mission_phase: str = "idle"  # idle, observing, maneuvering, communicating
        self.target_contact: Optional[Contact] = None
    
    def _get_unit_type(self) -> str:
        """Return the unit type string. Override in subclasses."""
        return "space_generic"
    
    def _get_capabilities(self) -> List[AgentCapability]:
        """Return default capabilities. Override in subclasses."""
        return [
            AgentCapability.SENSE,
            AgentCapability.MOVE,
            AgentCapability.COMMUNICATE,
        ]
    
    def set_velocity(self, velocity: Tuple[float, float, float]) -> None:
        """Set orbital velocity vector in km/s."""
        self.velocity = velocity
    
    def apply_delta_v(self, delta_v: float, direction: str = "prograde") -> bool:
        """
        Apply delta-v (change in velocity) for orbital maneuvers.
        
        Args:
            delta_v: Delta-v in m/s
            direction: "prograde", "retrograde", "normal", "anti-normal"
            
        Returns:
            True if maneuver successful
        """
        delta_v_km_s = delta_v / 1000.0  # Convert m/s to km/s
        
        if self.delta_v_remaining < delta_v_km_s:
            logger.warning(f"{self.unit.unit_id} insufficient delta-v for maneuver")
            return False
        
        self.delta_v_remaining -= delta_v_km_s
        
        # Update velocity based on direction
        if direction == "prograde":
            self.velocity = (
                self.velocity[0] + delta_v_km_s,
                self.velocity[1],
                self.velocity[2],
            )
        elif direction == "retrograde":
            self.velocity = (
                self.velocity[0] - delta_v_km_s,
                self.velocity[1],
                self.velocity[2],
            )
        
        return True
    
    def consume_power(self, amount: float) -> bool:
        """
        Consume power. Returns True if power available.
        
        Args:
            amount: Amount of power to consume (0.0-1.0)
        """
        if self.power_level >= amount:
            self.power_level = max(0.0, self.power_level - amount)
            return True
        return False
    
    def update(self, world_state: Any, delta_time: float = 1.0) -> None:
        """
        Update space agent state.
        
        Handles:
        - Orbital propagation
        - Power consumption
        - Sensor updates
        - Communication delays
        """
        # Consume power for active systems
        if self.sensor_active:
            power_consumption = 0.001 * delta_time
            self.consume_power(power_consumption)
        
        # Check power status
        if self.power_level <= 0.0:
            self.sensor_active = False
            logger.warning(f"{self.unit.unit_id} power depleted, sensors offline")
        
        # Update position based on orbital motion (simplified)
        if self.velocity[0] > 0:
            # Simple orbital propagation
            speed_km_s = self.velocity[0]
            update_km = speed_km_s * delta_time
            self.unit.position = (
                (self.unit.position[0] + update_km) % 20000,  # Wrap around Earth
                self.unit.position[1],
                self.unit.position[2],
            )
    
    def get_stats(self) -> dict:
        """Get space agent statistics."""
        stats = super().get_stats() if hasattr(super(), "get_stats") else {}
        stats.update({
            "orbital_altitude_km": self.orbital_altitude_km,
            "velocity": self.velocity,
            "delta_v_remaining": self.delta_v_remaining,
            "power_level": self.power_level,
            "communication_delay_ms": self.communication_delay_ms,
            "sensor_swath_km": self.sensor_swath_km,
            "sensor_active": self.sensor_active,
            "orbit_type": self.orbit_type,
            "orbital_period_minutes": self.orbital_period_minutes,
            "mission_phase": self.mission_phase,
        })
        return stats
    
    def to_dict(self) -> dict:
        """Serialize agent state."""
        data = super().to_dict()
        data.update({
            "orbital_altitude_km": self.orbital_altitude_km,
            "velocity": self.velocity,
            "delta_v_remaining": self.delta_v_remaining,
            "power_level": self.power_level,
            "communication_delay_ms": self.communication_delay_ms,
            "sensor_swath_km": self.sensor_swath_km,
            "sensor_active": self.sensor_active,
            "orbit_type": self.orbit_type,
            "orbital_period_minutes": self.orbital_period_minutes,
            "inclination_deg": self.inclination_deg,
            "mission_phase": self.mission_phase,
        })
        return data
    
    def from_dict(self, data: dict) -> None:
        """Deserialize agent state."""
        super().from_dict(data)
        self.orbital_altitude_km = data.get("orbital_altitude_km", self.orbital_altitude_km)
        self.velocity = data.get("velocity", self.velocity)
        self.delta_v_remaining = data.get("delta_v_remaining", self.delta_v_remaining)
        self.power_level = data.get("power_level", self.power_level)
        self.communication_delay_ms = data.get("communication_delay_ms", self.communication_delay_ms)
        self.sensor_swath_km = data.get("sensor_swath_km", self.sensor_swath_km)
        self.sensor_active = data.get("sensor_active", self.sensor_active)
        self.orbit_type = data.get("orbit_type", self.orbit_type)
        self.orbital_period_minutes = data.get("orbital_period_minutes", self.orbital_period_minutes)
        self.inclination_deg = data.get("inclination_deg", self.inclination_deg)
        self.mission_phase = data.get("mission_phase", self.mission_phase)