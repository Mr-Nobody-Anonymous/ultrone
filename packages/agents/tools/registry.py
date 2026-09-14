# Copyright (c) Ultrone Contributors. All rights reserved.
"""Tool Registry cataloging callable tools and schemas."""

from __future__ import annotations

from typing import Callable, Dict, List, Optional

from .schema import ToolDefinition


class ToolRegistry:
    """Central catalog of registered tools and their executable handlers."""

    def __init__(self) -> None:
        self._definitions: Dict[str, ToolDefinition] = {}
        self._implementations: Dict[str, Callable] = {}

    def register(self, definition: ToolDefinition, handler: Callable) -> None:
        """Register a tool with its schema definition and callable implementation."""
        self._definitions[definition.name] = definition
        self._implementations[definition.name] = handler

    def get_definition(self, name: str) -> Optional[ToolDefinition]:
        return self._definitions.get(name)

    def get_handler(self, name: str) -> Optional[Callable]:
        return self._implementations.get(name)

    def list_tools(self) -> List[ToolDefinition]:
        return list(self._definitions.values())
