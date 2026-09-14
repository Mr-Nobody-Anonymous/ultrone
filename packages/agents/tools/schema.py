# Copyright (c) Ultrone Contributors. All rights reserved.
"""Tool definition schemas and execution outcomes."""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class RiskLevel(str, Enum):
    """Risk tier of tool invocation."""

    LOW = "LOW"            # Read-only operations, safe lookups
    MEDIUM = "MEDIUM"      # Local memory updates, compute tasks
    HIGH = "HIGH"          # Code execution, file modifications
    CRITICAL = "CRITICAL"  # Physical machine actuation, network send, deletion


@dataclass
class ToolParameter:
    """Parameter definition for tool invocation."""

    name: str
    type: str = "string"
    description: str = ""
    required: bool = True
    default: Any = None


@dataclass
class ToolDefinition:
    """Formal schema definition of a callable tool."""

    name: str
    description: str
    parameters: List[ToolParameter] = field(default_factory=list)
    risk_level: RiskLevel = RiskLevel.LOW
    requires_approval: bool = False
    timeout_seconds: float = 30.0

    def validate_arguments(self, args: Dict[str, Any]) -> None:
        """Validate passed arguments against parameter requirements."""
        for param in self.parameters:
            if param.required and param.name not in args:
                raise ValueError(f"Missing required parameter '{param.name}' for tool '{self.name}'")


@dataclass
class ToolResult:
    """Result returned from tool execution."""

    tool_name: str
    success: bool
    output: Any = None
    error: Optional[str] = None
    duration_ms: float = 0.0
    execution_id: str = field(default_factory=lambda: f"tool-{uuid.uuid4().hex[:8]}")
    timestamp: float = field(default_factory=time.time)
