"""
Argus — Plugin System
=====================
Dynamic plugin discovery, registration, and lifecycle management.
"""

from .base import Plugin, PluginConfig, PluginContext, PluginRegistry
from .manager import PluginManager

__all__ = [
    "Plugin",
    "PluginConfig",
    "PluginContext",
    "PluginRegistry",
    "PluginManager",
]