# Copyright (c) Ultrone Contributors. All rights reserved.
"""Military configuration and doctrine presets."""

from .settings import MilitaryConfig, PerformanceConfig, ResearchPlatformConfig
from .doctrine_presets import DoctrinePreset, DoctrineType, get_doctrine_preset

__all__ = [
    "MilitaryConfig",
    "PerformanceConfig",
    "ResearchPlatformConfig",
    "DoctrinePreset",
    "DoctrineType",
    "get_doctrine_preset",
]