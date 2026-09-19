# Copyright (c) Ultrone Contributors. All rights reserved.
"""McpClient: Standard client communicating with MCP Servers via JSON-RPC 2.0."""

from __future__ import annotations

import json
import logging
import subprocess
import threading
from typing import Any, Dict, List, Optional, Union

from .protocol import (
    McpRequest,
    McpResource,
    McpResponse,
    McpToolDefinition,
    McpToolInputSchema,
    McpToolResult,
)
from .server import McpServer

logger = logging.getLogger("Ultrone.MCP.Client")


class McpClient:
    """Client implementing the Model Context Protocol."""

    def __init__(
        self,
        server: Optional[McpServer] = None,
        command: Optional[List[str]] = None,
        client_name: str = "ultrone-brain-client",
        client_version: str = "1.0.0",
    ) -> None:
        self.client_name = client_name
        self.client_version = client_version
        self._server = server
        self._command = command
        self._proc: Optional[subprocess.Popen[str]] = None
        self._request_counter: int = 0
        self._initialized: bool = False
        self._server_capabilities: Dict[str, Any] = {}

    def connect(self) -> Dict[str, Any]:
        """Establish connection and perform MCP initialization handshake."""
        if self._command and not self._server:
            self._proc = subprocess.Popen(
                self._command,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
            )

        resp = self.send_request(
            "initialize",
            {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {
                    "name": self.client_name,
                    "version": self.client_version,
                },
            },
        )
        if resp.error:
            raise RuntimeError(f"MCP Initialize failed: {resp.error}")

        self._initialized = True
        self._server_capabilities = resp.result.get("capabilities", {}) if resp.result else {}
        return resp.result or {}

    def list_tools(self) -> List[McpToolDefinition]:
        """Discover tools available on the connected MCP server."""
        resp = self.send_request("tools/list", {})
        if resp.error:
            raise RuntimeError(f"MCP tools/list failed: {resp.error}")

        tools_raw = (resp.result or {}).get("tools", [])
        tools: List[McpToolDefinition] = []
        for item in tools_raw:
            schema_data = item.get("inputSchema", {})
            schema = McpToolInputSchema(
                type=schema_data.get("type", "object"),
                properties=schema_data.get("properties", {}),
                required=schema_data.get("required", []),
                additionalProperties=schema_data.get("additionalProperties", False),
            )
            tools.append(
                McpToolDefinition(
                    name=item["name"],
                    description=item.get("description", ""),
                    inputSchema=schema,
                )
            )
        return tools

    def call_tool(self, name: str, arguments: Optional[Dict[str, Any]] = None) -> McpToolResult:
        """Invoke a tool on the MCP server."""
        resp = self.send_request(
            "tools/call",
            {"name": name, "arguments": arguments or {}},
        )
        if resp.error:
            return McpToolResult.error(f"RPC Error [{resp.error.get('code')}]: {resp.error.get('message')}")

        result_payload = resp.result or {}
        content_items = result_payload.get("content", [])
        is_error = result_payload.get("isError", False)

        from .protocol import McpTextContent

        parsed_content = [
            McpTextContent(type=item.get("type", "text"), text=item.get("text", ""))
            for item in content_items
        ]
        return McpToolResult(content=parsed_content, isError=is_error)

    def list_resources(self) -> List[McpResource]:
        """Discover resources available on the connected MCP server."""
        resp = self.send_request("resources/list", {})
        if resp.error:
            raise RuntimeError(f"MCP resources/list failed: {resp.error}")

        resources_raw = (resp.result or {}).get("resources", [])
        return [
            McpResource(
                uri=item["uri"],
                name=item["name"],
                description=item.get("description"),
                mimeType=item.get("mimeType", "application/json"),
            )
            for item in resources_raw
        ]

    def read_resource(self, uri: str) -> str:
        """Read text contents of an MCP resource by URI."""
        resp = self.send_request("resources/read", {"uri": uri})
        if resp.error:
            raise RuntimeError(f"MCP resources/read failed for '{uri}': {resp.error}")

        contents = (resp.result or {}).get("contents", [])
        if not contents:
            return ""
        return contents[0].get("text", "")

    def send_request(self, method: str, params: Dict[str, Any]) -> McpResponse:
        """Send a JSON-RPC request to the connected transport."""
        self._request_counter += 1
        req = McpRequest(id=self._request_counter, method=method, params=params)

        # 1. In-process direct server invocation
        if self._server is not None:
            return self._server.handle_request(req)

        # 2. Subprocess stdio transport
        if self._proc is not None and self._proc.stdin and self._proc.stdout:
            req_str = req.to_json() + "\n"
            self._proc.stdin.write(req_str)
            self._proc.stdin.flush()

            line = self._proc.stdout.readline()
            if not line:
                return McpResponse.error_response(
                    id=req.id,
                    code=-32000,
                    message="Subprocess stdio connection closed.",
                )
            data = json.loads(line)
            return McpResponse(
                id=data.get("id"),
                result=data.get("result"),
                error=data.get("error"),
            )

        raise RuntimeError("No MCP server or subprocess connected.")

    def close(self) -> None:
        """Terminate connected subprocess if active."""
        if self._proc is not None:
            try:
                self._proc.terminate()
                self._proc.wait(timeout=2.0)
            except Exception:
                self._proc.kill()
            self._proc = None
