# Copyright (c) Ultrone Contributors. All rights reserved.
"""Plugin discovery — discovers and loads plugins from directories."""

from __future__ import annotations

import importlib
import logging
import pkgutil
from pathlib import Path
from typing import Any, Dict, List, Optional

from .base import Plugin, PluginContext

logger = logging.getLogger("Ultrone.PluginSDK.Discovery")


class PluginDiscovery:
    """Discovers and loads plugins from directories and packages."""

    def __init__(self, plugin_dir: str = "plugins"):
        self.plugin_dir = Path(plugin_dir)
        self.plugin_dir.mkdir(parents=True, exist_ok=True)
        self._loaded_plugins: Dict[str, Plugin] = {}

    def discover(self) -> List[Plugin]:
        """Discover and load all plugins from the plugin directory."""
        plugins = []
        for path in self.plugin_dir.glob("*.py"):
            if path.name.startswith("_"):
                continue
            try:
                plugin = self._load_from_file(path)
                if plugin:
                    plugins.append(plugin)
                    self._loaded_plugins[plugin.plugin_id] = plugin
            except Exception as e:
                logger.error("Failed to load plugin %s: %s", path, e)
        return plugins

    def _load_from_file(self, path: Path) -> Optional[Plugin]:
        """Load a plugin from a Python file."""
        module_name = path.stem
        spec = importlib.util.spec_from_file_location(module_name, path)
        if spec is None or spec.loader is None:
            return None
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        # Find plugin class (subclass of Plugin)
        for attr_name in dir(module):
            attr = getattr(module, attr_name)
            if (
                isinstance(attr, type)
                and issubclass(attr, Plugin)
                and attr is not Plugin
            ):
                return attr()
        return None

    def load_package(self, package_name: str) -> List[Plugin]:
        """Load plugins from a Python package."""
        plugins = []
        try:
            package = importlib.import_module(package_name)
            for _, module_name, _ in pkgutil.iter_modules(package.__path__):
                try:
                    module = importlib.import_module(f"{package_name}.{module_name}")
                    for attr_name in dir(module):
                        attr = getattr(module, attr_name)
                        if (
                            isinstance(attr, type)
                            and issubclass(attr, Plugin)
                            and attr is not Plugin
                        ):
                            plugin = attr()
                            plugins.append(plugin)
                            self._loaded_plugins[plugin.plugin_id] = plugin
                except Exception as e:
                    logger.error("Failed to load plugin module %s: %s", module_name, e)
        except ImportError as e:
            logger.error("Failed to import package %s: %s", package_name, e)
        return plugins

    def get_plugin(self, plugin_id: str) -> Optional[Plugin]:
        """Get a loaded plugin by ID."""
        return self._loaded_plugins.get(plugin_id)

    def get_all_plugins(self) -> List[Plugin]:
        """Get all loaded plugins."""
        return list(self._loaded_plugins.values())

    def get_stats(self) -> Dict[str, Any]:
        return {
            "type": "PluginDiscovery",
            "plugin_dir": str(self.plugin_dir),
            "loaded_plugins": len(self._loaded_plugins),
        }