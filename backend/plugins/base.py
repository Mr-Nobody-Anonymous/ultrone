"""
Argus — Plugin Base Classes
===========================
Abstract plugin protocol with typed configuration, context, and registry.
"""

from __future__ import annotations

import importlib
import inspect
import pkgutil
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Type


@dataclass
class PluginConfig:
    """Configuration for a plugin."""

    name: str = ""
    version: str = "1.0.0"
    enabled: bool = True
    priority: int = 0
    config: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PluginContext:
    """Execution context passed to plugins."""

    plugin_id: str = ""
    timestamp: datetime = field(default_factory=datetime.utcnow)
    services: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def get_service(self, name: str) -> Optional[Any]:
        return self.services.get(name)

    def register_service(self, name: str, service: Any) -> None:
        self.services[name] = service


class Plugin(ABC):
    """Abstract base class for all plugins."""

    name: str = "base"
    version: str = "1.0.0"

    def __init__(self, config: Optional[PluginConfig] = None) -> None:
        self.config = config or PluginConfig(name=self.name)
        self._context: Optional[PluginContext] = None
        self._initialized: bool = False

    @abstractmethod
    def initialize(self, context: PluginContext) -> None:
        """Initialize the plugin with a context."""
        ...

    @abstractmethod
    def execute(self, **kwargs: Any) -> Any:
        """Execute the plugin's main logic."""
        ...

    def shutdown(self) -> None:
        """Clean up plugin resources."""
        self._initialized = False

    @property
    def is_initialized(self) -> bool:
        return self._initialized


class PluginRegistry:
    """Registry for plugin discovery and lookup."""

    def __init__(self) -> None:
        self._plugins: Dict[str, Plugin] = {}
        self._factories: Dict[str, Callable[..., Plugin]] = {}

    def register(self, plugin: Plugin) -> None:
        """Register a plugin instance."""
        self._plugins[plugin.name] = plugin

    def register_factory(
        self, name: str, factory: Callable[..., Plugin]
    ) -> None:
        """Register a plugin factory."""
        self._factories[name] = factory

    def unregister(self, name: str) -> bool:
        """Unregister a plugin."""
        removed = self._plugins.pop(name, None) is not None
        self._factories.pop(name, None)
        return removed

    def get(self, name: str) -> Optional[Plugin]:
        """Get a registered plugin by name."""
        plugin = self._plugins.get(name)
        if plugin is not None:
            return plugin
        factory = self._factories.get(name)
        if factory is not None:
            plugin = factory()
            self._plugins[name] = plugin
            return plugin
        return None

    def all(self) -> List[Plugin]:
        """Return all registered plugins."""
        return list(self._plugins.values())

    def names(self) -> List[str]:
        """Return all registered plugin names."""
        return list(self._plugins.keys()) + list(self._factories.keys())

    def count(self) -> int:
        return len(self._plugins) + len(self._factories)

    def discover(self, package: str) -> int:
        """Discover plugins in a package by scanning for Plugin subclasses."""
        try:
            mod = importlib.import_module(package)
        except ImportError:
            return 0

        count = 0
        if hasattr(mod, "__path__"):
            for _, modname, _ in pkgutil.iter_modules(mod.__path__):
                full_name = f"{package}.{modname}"
                try:
                    sub_mod = importlib.import_module(full_name)
                    for _, obj in inspect.getmembers(sub_mod, inspect.isclass):
                        if (
                            issubclass(obj, Plugin)
                            and obj is not Plugin
                            and obj.__module__ == full_name
                        ):
                            try:
                                instance = obj()
                                self.register(instance)
                                count += 1
                            except Exception:
                                pass
                except Exception:
                    pass
        return count