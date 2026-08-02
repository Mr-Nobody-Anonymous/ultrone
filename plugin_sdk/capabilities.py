# Copyright (c) Ultrone Contributors. All rights reserved.
"""Plugin capabilities — declares and validates plugin capabilities."""

from __future__ import annotations

import logging
from enum import Enum
from typing import Any, Dict, List, Optional, Set

from .base import Plugin, PluginType

logger = logging.getLogger("Ultrone.PluginSDK.Capabilities")


class Capability(Enum):
    """Capabilities a plugin can declare."""
    TRAINING = "training"
    INFERENCE = "inference"
    OPTIMIZATION = "optimization"
    SEARCH = "search"
    PLANNING = "planning"
    MEMORY = "memory"
    SENSING = "sensing"
    SIMULATION = "simulation"
    VISUALIZATION = "visualization"
    DATA_LOADING = "data_loading"
    EVALUATION = "evaluation"
    GENERATION = "generation"


class PluginCapabilities:
    """Declares and validates plugin capabilities."""

    # Mapping of plugin types to default capabilities
    DEFAULT_CAPABILITIES: Dict[PluginType, Set[Capability]] = {
        PluginType.ALGORITHM: {Capability.TRAINING, Capability.INFERENCE},
        PluginType.PLANNER: {Capability.PLANNING, Capability.SEARCH},
        PluginType.RL_METHOD: {Capability.TRAINING, Capability.OPTIMIZATION},
        PluginType.OPTIMIZATION: {Capability.OPTIMIZATION},
        PluginType.SENSOR: {Capability.SENSING},
        PluginType.SIMULATOR: {Capability.SIMULATION},
        PluginType.MEMORY: {Capability.MEMORY},
        PluginType.VISUALIZATION: {Capability.VISUALIZATION},
        PluginType.DATASET: {Capability.DATA_LOADING},
        PluginType.EXPERIMENT_PIPELINE: {Capability.TRAINING, Capability.EVALUATION},
        PluginType.LLM_PROVIDER: {Capability.GENERATION, Capability.INFERENCE},
        PluginType.EVALUATION_METRIC: {Capability.EVALUATION},
    }

    def __init__(self, plugin: Plugin):
        self.plugin = plugin
        self._capabilities: Set[Capability] = set(
            self.DEFAULT_CAPABILITIES.get(plugin.plugin_type, set())
        )

    def add_capability(self, capability: Capability) -> None:
        """Add a capability to the plugin."""
        self._capabilities.add(capability)

    def remove_capability(self, capability: Capability) -> None:
        """Remove a capability from the plugin."""
        self._capabilities.discard(capability)

    def has_capability(self, capability: Capability) -> bool:
        """Check if the plugin has a capability."""
        return capability in self._capabilities

    def get_capabilities(self) -> List[str]:
        """Get all capabilities as strings."""
        return [c.value for c in self._capabilities]

    def validate(self) -> List[str]:
        """Validate that the plugin meets its type's required capabilities."""
        required = self.DEFAULT_CAPABILITIES.get(self.plugin.plugin_type, set())
        missing = required - self._capabilities
        return [f"Missing required capability: {c.value}" for c in missing]

    def get_stats(self) -> Dict[str, Any]:
        return {
            "plugin_id": self.plugin.plugin_id,
            "plugin_name": self.plugin.name,
            "plugin_type": self.plugin.plugin_type.value,
            "capabilities": self.get_capabilities(),
            "validation_issues": self.validate(),
        }