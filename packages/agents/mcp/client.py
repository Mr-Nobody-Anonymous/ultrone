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
    McpRequestMetadata,
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

    def discover(self) -> Dict[str, Any]:
        """MCP 2026-07-28 stateless server discovery."""
        resp = self.send_request("server/discover", {})
        if resp.error:
            raise RuntimeError(f"MCP server/discover failed: {resp.error}")
        self._server_capabilities = resp.result.get("capabilities", {}) if resp.result else {}
        return resp.result or {}

    def connect(self) -> Dict[str, Any]:
        """Establish connection and perform discovery (or backward-compatible initialization)."""
        if self._command and not self._server:
            self._proc = subprocess.Popen(
                self._command,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
            )

        # Attempt modern 2026-07-28 discover first
        try:
            res = self.discover()
            self._initialized = True
            return res
        except Exception:
            # Fallback for legacy 2024 servers
            resp = self.send_request(
                "initialize",
                {
                    "protocolVersion": "2026-07-28",
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

    def call_mrtr_step(self, token: str, step_input: Dict[str, Any]) -> McpResponse:
        """Execute a Multi Round-Trip Request (MRTR) continuation step."""
        meta = McpRequestMetadata(
            protocol_version="2026-07-28",
            client_info={"name": self.client_name, "version": self.client_version},
            round_trip_token=token,
        )
        return self.send_request("mrtr/step", {"round_trip_token": token, "input": step_input}, metadata=meta)

    def call_tool_mrtr(
        self,
        name: str,
        arguments: Optional[Dict[str, Any]] = None,
        input_responder: Optional[Callable[[List[Dict[str, Any]]], List[Dict[str, Any]]]] = None,
    ) -> McpResponse:
        """Execute a tool call with automatic official MRTR input resolution."""
        initial_resp = self.send_request("tools/call", {"name": name, "arguments": arguments or {}})
        if initial_resp.error:
            return initial_resp

        res = initial_resp.result or {}
        if res.get("resultType") == "input_required":
            token = res.get("roundTripToken")
            requests = res.get("inputRequests", [])
            responses = input_responder(requests) if input_responder else []
            meta = McpRequestMetadata(
                protocol_version="2026-07-28",
                client_info={"name": self.client_name, "version": self.client_version},
                round_trip_token=token,
                input_responses=responses,
            )
            return self.send_request(
                "tools/call",
                {
                    "name": name,
                    "arguments": arguments or {},
                    "roundTripToken": token,
                    "inputResponses": responses,
                },
                metadata=meta,
            )
        return initial_resp

    def send_request(
        self,
        method: str,
        params: Dict[str, Any],
        metadata: Optional[McpRequestMetadata] = None,
    ) -> McpResponse:
        """Send a JSON-RPC request carrying MCP 2026-07-28 metadata to the transport."""
        self._request_counter += 1
        req_meta = metadata or McpRequestMetadata(
            protocol_version="2026-07-28",
            client_info={"name": self.client_name, "version": self.client_version},
        )
        req = McpRequest(id=self._request_counter, method=method, params=params, metadata=req_meta)

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
