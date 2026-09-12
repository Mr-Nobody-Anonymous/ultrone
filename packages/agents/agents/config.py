# Copyright (c) Ultrone Contributors. All rights reserved.
"""Agent configuration dataclasses for all domains."""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple
from enum import Enum

from data.entities import DomainType

logger = logging.getLogger("Ultrone.Agents.Config")


class AgentStatus(Enum):
    """Agent lifecycle status."""
    INITIALIZED = "initialized"
    READY = "ready"
    ACTIVE = "active"
    PAUSED = "paused"
    DEGRADED = "degraded"
    INACTIVE = "inactive"


@dataclass
class AgentConfig:
    """Base configuration for all agents."""
    agent_id: str = ""
    name: str = ""
    team: str = "blue"
    domain: DomainType = DomainType.GENERAL
    status: AgentStatus = AgentStatus.INITIALIZED
    seed: Optional[int] = None
    
    # Resource limits
    max_health: float = 1.0
    max_fuel: float = 1.0
    max_ammunition: int = 100
    
    # Sensor configuration
    sensor_range: float = 50000.0
    sensor_update_interval: float = 1.0
    
    # Communication
    enable_communications: bool = True
    communication_range: float = 100000.0
    
    # Simulation
    deterministic: bool = True
    max_actions_per_turn: int = 1
    
    # Telemetry
    enable_telemetry: bool = True
    
    # Custom parameters
    extra: Dict[str, Any] = field(default_factory=dict)
    
    def validate(self) -> None:
        """Validate configuration parameters."""
        if self.max_health <= 0:
            raise ValueError("max_health must be positive")
        if self.sensor_range < 0:
            raise ValueError("sensor_range must be non-negative")
        if self.max_actions_per_turn < 1:
            raise ValueError("max_actions_per_turn must be at least 1")


@dataclass
class AirAgentConfig(AgentConfig):
    """Configuration for air domain agents."""
    domain: DomainType = DomainType.AIR
    max_altitude: float = 10000.0
    cruise_altitude: float = 5000.0
    max_speed: float = 300.0
    fuel_consumption_rate: float = 0.01
    stealth_factor: float = 0.0
    payload_capacity: int = 1000
    
    def validate(self) -> None:
        super().validate()
        if self.max_altitude <= 0:
            raise ValueError("max_altitude must be positive")
        if self.cruise_altitude > self.max_altitude:
            raise ValueError("cruise_altitude cannot exceed max_altitude")


@dataclass
class LandAgentConfig(AgentConfig):
    """Configuration for land domain agents."""
    domain: DomainType = DomainType.LAND
    max_speed: float = 50.0
    terrain_compatibility: List[str] = field(default_factory=lambda: ["road", "dirt", "grass"])
    armor_rating: float = 1.0
    weapon_range: float = 3000.0
    
    def validate(self) -> None:
        super().validate()
        if not self.terrain_compatibility:
            raise ValueError("terrain_compatibility must not be empty")


@dataclass
class SeaAgentConfig(AgentConfig):
    """Configuration for sea domain agents."""
    domain: DomainType = DomainType.SEA
    max_speed: float = 30.0
    max_depth: float = 500.0
    displacement: float = 1000.0
    stealth_factor: float = 0.1
    sonar_range: float = 50000.0
    
    def validate(self) -> None:
        super().validate()
        if self.max_depth <= 0:
            raise ValueError("max_depth must be positive")


@dataclass
class SpaceAgentConfig(AgentConfig):
    """Configuration for space domain agents."""
    domain: DomainType = DomainType.SPACE
    orbital_altitude_km: float = 500.0
    delta_v_capacity: float = 1000.0
    power_capacity: float = 1.0
    communication_delay_ms: float = 250.0
    sensor_swath_km: float = 100.0
    
    def validate(self) -> None:
        super().validate()
        if self.orbital_altitude_km < 160:
            raise ValueError("orbital_altitude_km must be at least 160 km (LEO)")
        if self.delta_v_capacity < 0:
            raise ValueError("delta_v_capacity must be non-negative")


@dataclass
class CyberAgentConfig(AgentConfig):
    """Configuration for cyber domain agents."""
    domain: DomainType = DomainType.CYBER
    compute_nodes: int = 4
    bandwidth_mbps: float = 1000.0
    encryption_strength: float = 1.0
    stealth_factor: float = 0.5
    exploit_success_rate: float = 0.7
    
    def validate(self) -> None:
        super().validate()
        if self.compute_nodes < 1:
            raise ValueError("compute_nodes must be at least 1")
        if not 0.0 <= self.exploit_success_rate <= 1.0:
            raise ValueError("exploit_success_rate must be between 0 and 1")


def get_config_for_domain(domain: DomainType) -> AgentConfig:
    """Factory function to get default config for a domain."""
    configs = {
        DomainType.AIR: AirAgentConfig,
        DomainType.LAND: LandAgentConfig,
        DomainType.SEA: SeaAgentConfig,
        DomainType.SPACE: SpaceAgentConfig,
        DomainType.CYBER: CyberAgentConfig,
        DomainType.GENERAL: AgentConfig,
    }
    config_class = configs.get(domain, AgentConfig)
    return config_class()