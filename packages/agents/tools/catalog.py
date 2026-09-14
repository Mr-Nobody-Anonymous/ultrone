# Copyright (c) Ultrone Contributors. All rights reserved.
"""Tool security catalog defining standardized tools and risk boundaries."""

from __future__ import annotations

from typing import Dict, List

from .registry import ToolRegistry
from .schema import RiskLevel, ToolDefinition, ToolParameter


def create_standard_tool_catalog() -> ToolRegistry:
    """Construct and populate standard registry with vetted tools and risk tiers."""
    registry = ToolRegistry()

    # 1. Read-only tools (RiskLevel.LOW)
    registry.register(
        ToolDefinition(
            name="file_read",
            description="Reads text content of a file within the workspace",
            parameters=[ToolParameter(name="path", type="string", required=True)],
            risk_level=RiskLevel.LOW,
            requires_approval=False,
        ),
        lambda path: f"[Simulated Content of {path}]",
    )

    registry.register(
        ToolDefinition(
            name="memory_search",
            description="Searches episodic and semantic memory",
            parameters=[ToolParameter(name="query", type="string", required=True)],
            risk_level=RiskLevel.LOW,
            requires_approval=False,
        ),
        lambda query: f"[Memory matches for: {query}]",
    )

    # 2. Local compute and state tools (RiskLevel.MEDIUM)
    registry.register(
        ToolDefinition(
            name="compute_metric",
            description="Computes statistical or performance metrics over an array",
            parameters=[
                ToolParameter(name="metric_name", type="string", required=True),
                ToolParameter(name="values", type="list", required=True),
            ],
            risk_level=RiskLevel.MEDIUM,
            requires_approval=False,
        ),
        lambda metric_name, values: sum(values) / max(1, len(values)),
    )

    # 3. High-risk write and execution tools (RiskLevel.HIGH)
    registry.register(
        ToolDefinition(
            name="file_write",
            description="Writes or updates file contents on disk",
            parameters=[
                ToolParameter(name="path", type="string", required=True),
                ToolParameter(name="content", type="string", required=True),
            ],
            risk_level=RiskLevel.HIGH,
            requires_approval=False,
        ),
        lambda path, content: {"bytes_written": len(content), "path": path},
    )

    # 4. Critical-risk actuator and network tools (RiskLevel.CRITICAL - requires approval)
    registry.register(
        ToolDefinition(
            name="actuate_physical_machine",
            description="Commands physical or simulated hardware actuator",
            parameters=[
                ToolParameter(name="machine_id", type="string", required=True),
                ToolParameter(name="command", type="string", required=True),
            ],
            risk_level=RiskLevel.CRITICAL,
            requires_approval=True,
        ),
        lambda machine_id, command: {"actuated": True, "machine": machine_id, "cmd": command},
    )

    registry.register(
        ToolDefinition(
            name="network_penetration_exploit",
            description="Executes cyber payload or penetration test exploit",
            parameters=[
                ToolParameter(name="target_ip", type="string", required=True),
                ToolParameter(name="payload", type="string", required=True),
            ],
            risk_level=RiskLevel.CRITICAL,
            requires_approval=True,
        ),
        lambda target_ip, payload: {"exploited": True, "target": target_ip},
    )

    return registry
