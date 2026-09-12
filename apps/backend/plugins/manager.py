"""
Argus — Plugin Manager
======================
Manages plugin lifecycle: discovery, initialization, execution, shutdown.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from .base import Plugin, PluginConfig, PluginContext, PluginRegistry


class PluginManager:
    """Manages the full plugin lifecycle."""

    def __init__(self, registry: Optional[PluginRegistry] = None) -> None:
        self._registry = registry or PluginRegistry()
        self._context = PluginContext()
        self._execution_count: int = 0
        self._errors: List[str] = []

    @property
    def registry(self) -> PluginRegistry:
        return self._registry

    def register(self, plugin: Plugin) -> None:
        """Register and initialize a plugin."""
        self._registry.register(plugin)
        if plugin.config.enabled:
            ctx = PluginContext(
                plugin_id=plugin.name,
                services=self._context.services,
            )
            plugin.initialize(ctx)
            plugin._initialized = True

    def initialize_all(self) -> int:
        """Initialize all registered plugins."""
        count = 0
        for plugin in self._registry.all():
            if not plugin.is_initialized and plugin.config.enabled:
                ctx = PluginContext(
                    plugin_id=plugin.name,
                    services=self._context.services,
                )
                try:
                    plugin.initialize(ctx)
                    plugin._initialized = True
                    count += 1
                except Exception as e:
                    self._errors.append(f"{plugin.name}: {e}")
        return count

    def execute(self, name: str, **kwargs: Any) -> Any:
        """Execute a specific plugin by name."""
        plugin = self._registry.get(name)
        if plugin is None:
            raise KeyError(f"Plugin not found: {name}")
        if not plugin.is_initialized:
            raise RuntimeError(f"Plugin not initialized: {name}")
        self._execution_count += 1
        return plugin.execute(**kwargs)

    def execute_all(self, **kwargs: Any) -> Dict[str, Any]:
        """Execute all initialized plugins."""
        results: Dict[str, Any] = {}
        for plugin in self._registry.all():
            if plugin.is_initialized:
                try:
                    results[plugin.name] = plugin.execute(**kwargs)
                except Exception as e:
                    self._errors.append(f"{plugin.name}: {e}")
                    results[plugin.name] = None
        return results

    def shutdown_all(self) -> int:
        """Shut down all plugins."""
        count = 0
        for plugin in self._registry.all():
            if plugin.is_initialized:
                plugin.shutdown()
                count += 1
        return count

    def discover(self, package: str) -> int:
        """Discover plugins in a package."""
        return self._registry.discover(package)

    def register_service(self, name: str, service: Any) -> None:
        """Register a shared service available to all plugins."""
        self._context.register_service(name, service)

    def get_service(self, name: str) -> Optional[Any]:
        return self._context.get_service(name)

    @property
    def execution_count(self) -> int:
        return self._execution_count

    @property
    def errors(self) -> List[str]:
        return list(self._errors)

    def clear_errors(self) -> None:
        self._errors.clear()