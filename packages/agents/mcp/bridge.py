# Copyright (c) Ultrone Contributors. All rights reserved.
"""McpToolBridge: Bridges MCP Client tools into ULTRONE ToolRegistry & ToolRuntime."""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional

from packages.agents.tools.registry import ToolRegistry
from packages.agents.tools.schema import RiskLevel, ToolDefinition, ToolParameter, ToolResult
from .client import McpClient
from .protocol import McpToolDefinition

logger = logging.getLogger("Ultrone.MCP.Bridge")


class McpToolBridge:
    """Synchronizes external/internal MCP tools into the ULTRONE ToolRegistry."""

    def __init__(self, client: McpClient, registry: Optional[ToolRegistry] = None) -> None:
        self.client = client
        self.registry = registry or ToolRegistry()

    def sync_tools(
        self,
        risk_level_overrides: Optional[Dict[str, RiskLevel]] = None,
        approval_overrides: Optional[Dict[str, bool]] = None,
    ) -> List[str]:
        """Discover tools on MCP server and register them into ToolRegistry."""
        risk_map = risk_level_overrides or {}
        approval_map = approval_overrides or {}
        registered_names: List[str] = []

        mcp_tools = self.client.list_tools()
        for mcp_tool in mcp_tools:
            tool_def = self._convert_mcp_tool(mcp_tool, risk_map, approval_map)

            # Handler routes through MCP client
            def make_handler(name: str):
                def handler(**kwargs: Any) -> Any:
                    result = self.client.call_tool(name, kwargs)
                    if result.isError:
                        err_text = " ".join(c.text for c in result.content)
                        raise RuntimeError(f"MCP Tool '{name}' error: {err_text}")
                    if not result.content:
                        return None
                    raw_text = result.content[0].text
                    try:
                        return json.loads(raw_text)
                    except Exception:
                        return raw_text

                return handler

            self.registry.register(tool_def, make_handler(mcp_tool.name))
            registered_names.append(mcp_tool.name)
            logger.info("Bridged MCP tool '%s' into ULTRONE registry", mcp_tool.name)

        return registered_names

    def _convert_mcp_tool(
        self,
        mcp_tool: McpToolDefinition,
        risk_map: Dict[str, RiskLevel],
        approval_map: Dict[str, bool],
    ) -> ToolDefinition:
        schema = mcp_tool.inputSchema
        props = schema.properties if hasattr(schema, "properties") else schema.get("properties", {})
        required = set(schema.required if hasattr(schema, "required") else schema.get("required", []))

        params: List[ToolParameter] = []
        for prop_name, prop_meta in props.items():
            param_type = prop_meta.get("type", "string")
            param_desc = prop_meta.get("description")
            is_req = prop_name in required
            params.append(
                ToolParameter(
                    name=prop_name,
                    type=param_type,
                    description=param_desc,
                    required=is_req,
                )
            )

        # Infer default risk based on naming
        name_lower = mcp_tool.name.lower()
        if any(k in name_lower for k in ["strike", "engage", "destroy", "kill", "exploit"]):
            default_risk = RiskLevel.CRITICAL
            default_approval = True
        elif any(k in name_lower for k in ["actuate", "dispatch", "jamming", "write"]):
            default_risk = RiskLevel.HIGH
            default_approval = False
        elif any(k in name_lower for k in ["compute", "process", "filter"]):
            default_risk = RiskLevel.MEDIUM
            default_approval = False
        else:
            default_risk = RiskLevel.LOW
            default_approval = False

        risk = risk_map.get(mcp_tool.name, default_risk)
        requires_approval = approval_map.get(mcp_tool.name, default_approval)

        return ToolDefinition(
            name=mcp_tool.name,
            description=mcp_tool.description,
            parameters=params,
            risk_level=risk,
            requires_approval=requires_approval,
        )
