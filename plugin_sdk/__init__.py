# Copyright (c) Ultrone Contributors. All rights reserved.
"""Plugin SDK — hot-swappable plugin system for ULTRONE.

Plugins can provide new algorithms, planners, RL methods, optimization
engines, sensors, simulators, memory systems, visualizations, datasets,
experiment pipelines, LLM providers, and evaluation metrics.
"""

from .base import Plugin, PluginType, PluginContext
from .discovery import PluginDiscovery
from .capabilities import PluginCapabilities

__all__ = [
    "Plugin",
    "PluginType",
    "PluginContext",
    "PluginDiscovery",
    "PluginCapabilities",
]
