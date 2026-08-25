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


@dataclass
class ResearchPlatformConfig:
    """
    Configuration for the ULTRONE autonomous research platform.

    Controls the research division agents, knowledge engine layers,
    self-improvement loop, plugin system, and research database.
    """

    # Research division
    enable_research_division: bool = True
    research_poll_interval_seconds: float = 3600.0
    research_agent_pool_size: int = 4
    max_papers_per_cycle: int = 20

    # Research sources to monitor
    monitor_arxiv: bool = True
    monitor_semantic_scholar: bool = True
    monitor_huggingface: bool = True
    monitor_papers_with_code: bool = True
    monitor_openreview: bool = True
    monitor_github: bool = True
    monitor_conferences: bool = True
    monitor_leaderboards: bool = True

    # Knowledge engine
    knowledge_embedding_dim: int = 768
    knowledge_graph_enabled: bool = True
    vector_memory_enabled: bool = True
    ontology_enabled: bool = True
    entity_linking_enabled: bool = True
    rag_enabled: bool = True
    confidence_threshold: float = 0.6
    max_knowledge_entries: int = 100_000

    # Self-improvement
    enable_self_improvement: bool = True
    improvement_loop_interval_seconds: float = 86400.0
    max_concurrent_improvements: int = 3
    require_benchmark_gain: float = 0.02  # min relative improvement to adopt

    # Plugin system
    enable_plugins: bool = True
    plugin_dir: str = "plugins"
    hot_reload: bool = True

    # Research database
    research_db_path: str = "research_db"
    research_db_backend: str = "json"  # json, sqlite

    # Logging
    log_research_events: bool = True
    log_dir: str = "logs"
    log_to_json: bool = True
    log_to_markdown: bool = True
    log_to_sqlite: bool = True
    log_to_vector: bool = True
    log_to_knowledge_graph: bool = True

    def to_dict(self) -> dict:
        return {
            "enable_research_division": self.enable_research_division,
            "research_poll_interval_seconds": self.research_poll_interval_seconds,
            "monitor_arxiv": self.monitor_arxiv,
            "monitor_semantic_scholar": self.monitor_semantic_scholar,
            "enable_self_improvement": self.enable_self_improvement,
            "enable_plugins": self.enable_plugins,
            "research_db_backend": self.research_db_backend,
            "confidence_threshold": self.confidence_threshold,
            "knowledge_embedding_dim": self.knowledge_embedding_dim,
        }


@dataclass
class PerformanceConfig:
    """Central performance configuration for the ULTRONE runtime.

    Controls device selection, precision, compilation, quantization,
    batching, caching, and reasoning scheduling. All fields default to
    "auto" so the runtime picks safe, hardware-appropriate defaults.
    """

    device: str = "auto"      # auto, cpu, cuda, mps, rocm
    precision: str = "auto"   # auto, fp32, fp16, bf16, int8
    compile: str = "auto"     # off, auto, on
    quantization: str = "auto"  # none, int8, int4, auto
    max_batch_size: int = 8
    inference_timeout: float = 30.0
    enable_model_cache: bool = True
    enable_embedding_cache: bool = True
    enable_reasoning_cache: bool = True
    enable_async_inference: bool = True
    enable_xai: bool = False
    reasoning_interval: int = 5
    performance_profile: str = "auto"  # ultra_fast, balanced, research, max_quality
    max_cached_models: int = 8
    enable_eviction: bool = True
    warmup_enabled: bool = False

    def to_runtime_config(self):
        """Convert to a RuntimeConfig for the runtime subsystem."""
        from runtime import RuntimeConfig
        return RuntimeConfig(
            device=self.device,
            precision=self.precision,
            compile=self.compile,
            quantization=self.quantization,
            max_batch_size=self.max_batch_size,
            inference_timeout=self.inference_timeout,
            enable_model_cache=self.enable_model_cache,
            enable_embedding_cache=self.enable_embedding_cache,
            enable_reasoning_cache=self.enable_reasoning_cache,
            enable_async_inference=self.enable_async_inference,
            enable_xai=self.enable_xai,
            reasoning_interval=self.reasoning_interval,
            performance_profile=self.performance_profile,
            max_cached_models=self.max_cached_models,
            enable_eviction=self.enable_eviction,
            warmup_enabled=self.warmup_enabled,
        )

    def to_dict(self) -> dict:
        return {
            "device": self.device,
            "precision": self.precision,
            "compile": self.compile,
            "quantization": self.quantization,
            "max_batch_size": self.max_batch_size,
            "inference_timeout": self.inference_timeout,
            "enable_model_cache": self.enable_model_cache,
            "enable_embedding_cache": self.enable_embedding_cache,
            "enable_reasoning_cache": self.enable_reasoning_cache,
            "enable_async_inference": self.enable_async_inference,
            "enable_xai": self.enable_xai,
            "reasoning_interval": self.reasoning_interval,
            "performance_profile": self.performance_profile,
            "max_cached_models": self.max_cached_models,
            "enable_eviction": self.enable_eviction,
            "warmup_enabled": self.warmup_enabled,
        }


# Default configuration instance
default_config = MilitaryConfig()
default_performance_config = PerformanceConfig()
