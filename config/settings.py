# Copyright (c) Ultrone Contributors. All rights reserved.
"""Military simulation configuration settings."""

import os
from dataclasses import dataclass, field
from typing import Dict, Any, Optional


@dataclass
class MilitaryConfig:
    """
    Military simulation tuning parameters.
    
    Configuration for tick rates, thresholds, domain capabilities,
    and simulation parameters.
    """
    
    # Simulation timing
    tick_duration_seconds: float = 1.0
    simulation_acceleration: int = 10  # 1x, 2x, 5x, 10x, 100x
    max_ticks: int = 1000
    
    # Battlefield dimensions
    battlefield_width_km: int = 100
    battlefield_height_km: int = 100
    
    # Threat thresholds (per doctrine)
    threat_threshold_high: float = 0.8
    threat_threshold_medium: float = 0.5
    threat_threshold_low: float = 0.2
    
    # Engagement rules
    rules_of_engagement: str = "armed_forces_immediate"  # immediate, proportional, restricted
    collateral_acceptance_rate: float = 0.05  # Max acceptable collateral damage
    
    # Sensor parameters
    radar_detection_range_km: float = 150.0
    visual_detection_range_km: float = 20.0
    sigint_detection_range_km: float = 300.0
    
    # Kill chain timing
    kill_chain_time_limit_seconds: int = 300
    phase_timeout_seconds: int = 60
    
    # Evolution parameters
    evolution_enabled: bool = True
    evolution_interval_ticks: int = 10
    min_fitness_threshold: float = 0.75
    
    # Domain-specific settings
    domain_config: Dict[str, Any] = field(default_factory=lambda: {
        "air": {
            "patrol_altitude_meters": 10000,
            "intercept_altitude_meters": 8000,
            "max_speed_kmh": 900,
        },
        "land": {
            "max_speed_kmh": 60,
            "max_range_km": 20,
        },
        "sea": {
            "max_speed_kmh": 40,
            "max_range_km": 50,
        },
        "cyber": {
            "max_speed_kmh": 1,  # Not applicable
            "scan_range": "global",
        },
        "space": {
            "orbital_period_minutes": 90,
            "sensor_range_km": 500,
        },
    })
    
    # Logging configuration
    log_level: str = "INFO"
    log_classification: str = "UNCLASS"  # Minimum log classification level
    
    def get_domain_setting(self, domain: str, key: str, default: Any = None) -> Any:
        """Get a domain-specific configuration value."""
        return self.domain_config.get(domain, {}).get(key, default)
    
    def to_dict(self) -> dict:
        return {
            "tick_duration_seconds": self.tick_duration_seconds,
            "simulation_acceleration": self.simulation_acceleration,
            "battlefield_width_km": self.battlefield_width_km,
            "battlefield_height_km": self.battlefield_height_km,
            "threat_threshold_high": self.threat_threshold_high,
            "threat_threshold_medium": self.threat_threshold_medium,
            "threat_threshold_low": self.threat_threshold_low,
            "rules_of_engagement": self.rules_of_engagement,
            "collateral_acceptance_rate": self.collateral_acceptance_rate,
            "evolution_enabled": self.evolution_enabled,
            "evolution_interval_ticks": self.evolution_interval_ticks,
        }


# Default configuration instance
default_config = MilitaryConfig()