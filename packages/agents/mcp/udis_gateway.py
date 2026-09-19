# Copyright (c) Ultrone Contributors. All rights reserved.
"""UDIS MCP Gateway: Exposes Anthropic MHS-aligned UDIS devices via MCP 2026-07-28 tools & resources."""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional

from packages.runtime.device_protocol.registry import DeviceRegistry
from .protocol import McpRequest, McpResource, McpResponse, McpToolInputSchema
from .server import McpServer

logger = logging.getLogger("Ultrone.MCP.UDISGateway")


class UdisMcpGateway:
    """Bridges UDIS device discovery, state inspection, procedures, and leases into standard MCP."""

    def __init__(self, registry: DeviceRegistry, server_name: str = "ultrone-udis-gateway"):
        self.registry = registry
        self.server = McpServer(
            name=server_name,
            version="2026-07-28",
            capabilities={
                "tools": {"listChanged": True},
                "resources": {"subscribe": True, "listChanged": True},
            },
        )
        self._register_mhs_tools()
        self._register_mhs_resources()

    def _register_mhs_tools(self) -> None:
        """Register Anthropic MHS standard device discovery and execution tools."""

        # 1. devices_list
        self.server.register_tool(
            name="devices_list",
            description="Discover all registered UDIS devices, operating modes, and states.",
            input_schema=McpToolInputSchema(type="object", properties={}, required=[]),
            handler=lambda args: {"devices": self.registry.devices_list()},
        )

        # 2. devices_get
        self.server.register_tool(
            name="devices_get",
            description="Retrieve detailed manifest, specs, and telemetry for a specific device.",
            input_schema=McpToolInputSchema(
                type="object",
                properties={"device_id": {"type": "string", "description": "Target device ID"}},
                required=["device_id"],
            ),
            handler=lambda args: self.registry.devices_get(args["device_id"]) or {"error": "Not found"},
        )

        # 3. devices_capabilities
        self.server.register_tool(
            name="devices_capabilities",
            description="Retrieve capabilities, schemas, and lease requirements for a device.",
            input_schema=McpToolInputSchema(
                type="object",
                properties={"device_id": {"type": "string", "description": "Target device ID"}},
                required=["device_id"],
            ),
            handler=lambda args: {"capabilities": self.registry.devices_capabilities(args["device_id"])},
        )

        # 4. devices_state
        self.server.register_tool(
            name="devices_state",
            description="Inspect 10-state machine status, freshness, and active telemetry for a device.",
            input_schema=McpToolInputSchema(
                type="object",
                properties={"device_id": {"type": "string", "description": "Target device ID"}},
                required=["device_id"],
            ),
            handler=lambda args: self.registry.devices_state(args["device_id"]),
        )

        # 5. devices_procedures
        self.server.register_tool(
            name="devices_procedures",
            description="List compiled deterministic procedures supported by a device.",
            input_schema=McpToolInputSchema(
                type="object",
                properties={"device_id": {"type": "string", "description": "Target device ID"}},
                required=["device_id"],
            ),
            handler=lambda args: {"procedures": self.registry.devices_procedures(args["device_id"])},
        )

        # 6. request_lease
        self.server.register_tool(
            name="request_lease",
            description="Request a temporary capability-scoped lease before executing commands.",
            input_schema=McpToolInputSchema(
                type="object",
                properties={
                    "agent_id": {"type": "string"},
                    "device_id": {"type": "string"},
                    "capabilities": {"type": "array", "items": {"type": "string"}},
                    "duration_seconds": {"type": "number"},
                    "purpose": {"type": "string"},
                },
                required=["agent_id", "device_id", "capabilities"],
            ),
            handler=self._handle_request_lease,
        )

        # 7. execute_command
        self.server.register_tool(
            name="execute_command",
            description="Execute low-level command on device under an authorized capability lease.",
            input_schema=McpToolInputSchema(
                type="object",
                properties={
                    "device_id": {"type": "string"},
                    "command": {"type": "string"},
                    "params": {"type": "object"},
                    "lease_id": {"type": "string"},
                },
                required=["device_id", "command", "params"],
            ),
            handler=self._handle_execute_command,
        )

        # 8. execute_procedure
        self.server.register_tool(
            name="execute_procedure",
            description="Execute a validated deterministic procedure sequence on device.",
            input_schema=McpToolInputSchema(
                type="object",
                properties={
                    "device_id": {"type": "string"},
                    "procedure_name": {"type": "string"},
                    "params": {"type": "object"},
                    "lease_id": {"type": "string"},
                },
                required=["device_id", "procedure_name"],
            ),
            handler=self._handle_execute_procedure,
        )

    def _register_mhs_resources(self) -> None:
        """Register standard MCP dynamic resources."""
        self.server.register_resource(
            uri="udis://devices",
            name="UDIS Devices Inventory",
            description="Active inventory of all devices registered with UDIS",
            read_handler=lambda uri: json.dumps(self.registry.devices_list()),
        )

    def _handle_request_lease(self, args: Dict[str, Any]) -> Dict[str, Any]:
        lease = self.registry.lease_manager.request_lease(
            agent_id=args["agent_id"],
            device_id=args["device_id"],
            capabilities=set(args["capabilities"]),
            duration_seconds=float(args.get("duration_seconds", 300.0)),
            purpose=args.get("purpose", "tactical_task"),
            is_simulation=True,
        )
        return {
            "status": "granted",
            "lease_id": lease.lease_id,
            "granted_at": lease.granted_at,
            "expires_at": lease.expires_at,
            "capabilities": list(lease.capabilities),
        }

    def _handle_execute_command(self, args: Dict[str, Any]) -> Dict[str, Any]:
        res = self.registry.execute_command(
            device_id=args["device_id"],
            command=args["command"],
            params=args.get("params", {}),
            lease_id=args.get("lease_id"),
        )
        return {"status": "success", "result": res}

    def _handle_execute_procedure(self, args: Dict[str, Any]) -> Dict[str, Any]:
        result = self.registry.execute_procedure(
            device_id=args["device_id"],
            procedure_name=args["procedure_name"],
            params=args.get("params"),
            lease_id=args.get("lease_id"),
        )
        return {
            "procedure_id": result.procedure_id,
            "success": result.success,
            "steps_completed": result.steps_completed,
            "total_steps": result.total_steps,
            "duration_seconds": result.duration_seconds,
            "error": result.error,
        }

    def handle_request(self, request: McpRequest) -> McpResponse:
        """Dispatch JSON-RPC request to underlying McpServer."""
        return self.server.handle_request(request)
