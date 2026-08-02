# Copyright (c) Ultrone Contributors. All rights reserved.
"""Plugin SDK base — defines the plugin interface and types."""

from __future__ import annotations

import logging
import time
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger("Ultrone.PluginSDK")


class PluginType(Enum):
    """Types of plugins supported by ULTRONE."""
    ALGORITHM = "algorithm"
    PLANNER = "planner"
    RL_METHOD = "rl_method"
    OPTIMIZATION = "optimization"
    SENSOR = "sensor"
    SIMULATOR = "simulator"
    MEMORY = "memory"
    VISUALIZATION = "visualization"
    DATASET = "dataset"
    EXPERIMENT_PIPELINE = "experiment_pipeline"
    LLM_PROVIDER = "llm_provider"
    EVALUATION_METRIC = "evaluation_metric"


@dataclass
class PluginContext:
    """Context provided to plugins at runtime."""
    knowledge: Any = None
    research_db: Any = None
    message_bus: Any = None
    config: Dict[str, Any] = field(default_factory=dict)


class Plugin(ABC):
    """Base class for all ULTRONE plugins.

    Features
    --------
    - Unique plugin ID and version
    - Type declaration
    - Lifecycle hooks (initialize, activate, deactivate)
    - Capability declaration
    - Hot-swappable
    """

    def __init__(
        self,
        name: str,
        version: str = "1.0.0",
        plugin_type: PluginType = PluginType.ALGORITHM,
        description: str = "",
    ):
        self.plugin_id = f"PLG-{uuid.uuid4().hex[:8]}"
        self.name = name
        self.version = version
        self.plugin_type = plugin_type
        self.description = description
        self.context: Optional[PluginContext] = None
        self.active = False
        self.initialized = False
        self.created_at = time.time()

    def initialize(self, context: PluginContext) -> None:
        """Initialize the plugin with runtime context."""
        self.context = context
        self.initialized = True
        logger.info("Plugin %s initialized", self.name)

    def activate(self) -> None:
        """Activate the plugin."""
        self.active = True
        logger.info("Plugin %s activated", self.name)

    def deactivate(self) -> None:
        """Deactivate the plugin."""
        self.active = False
        logger.info("Plugin %s deactivated", self.name)

    def get_metadata(self) -> Dict[str, Any]:
        """Get plugin metadata."""
        return {
            "plugin_id": self.plugin_id,
            "name": self.name,
            "version": self.version,
            "type": self.plugin_type.value,
            "description": self.description,
            "active": self.active,
            "initialized": self.initialized,
        }

    @abstractmethod
    def execute(self, *args: Any, **kwargs: Any) -> Any:
        """Execute the plugin's primary function."""
        pass