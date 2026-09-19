# Copyright (c) Ultrone Contributors. All rights reserved.
"""McpServer: Server implementation exposing tools and resources via MCP JSON-RPC 2.0."""

from __future__ import annotations

import json
import logging
import time
import uuid
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

from .protocol import (
    McpErrorCode,
    McpInputRequest,
    McpInputResponse,
    McpMrtrResult,
    McpRequest,
    McpRequestMetadata,
    McpResource,
    McpResponse,
    McpTextContent,
    McpToolDefinition,
    McpToolInputSchema,
    McpToolResult,
)

logger = logging.getLogger("Ultrone.MCP.Server")


class McpServer:
    """Standard Model Context Protocol Server."""

    def __init__(
        self,
        name: str = "ultrone-mcp-server",
        version: str = "1.0.0",
        capabilities: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.name = name
        self.version = version
        self.capabilities = capabilities or {
            "tools": {"listChanged": False},
            "resources": {"subscribe": False, "listChanged": False},
        }
        self._tools: Dict[str, McpToolDefinition] = {}
        self._tool_handlers: Dict[str, Callable[[Dict[str, Any]], Union[Dict[str, Any], McpToolResult, str]]] = {}
        self._resources: Dict[str, McpResource] = {}
        self._resource_handlers: Dict[str, Callable[[str], Union[Dict[str, Any], str]]] = {}
        self._mrtr_sessions: Dict[str, Dict[str, Any]] = {}

    def create_mrtr_session(
        self,
        client_id: str,
        tool_name: str,
        arguments: Dict[str, Any],
        input_requests: List[Any],
        ttl_ms: int = 60000,
    ) -> str:
        """Create and store an active Multi Round-Trip Request (MRTR) session."""
        token = f"mrt_{uuid.uuid4().hex[:16]}"
        self._mrtr_sessions[token] = {
            "token": token,
            "client_id": client_id,
            "tool_name": tool_name,
            "arguments": arguments,
            "input_requests": input_requests,
            "expires_at": time.time() + (ttl_ms / 1000.0),
            "completed": False,
        }
        return token

    def register_tool(
        self,
        name: str,
        description: str,
        input_schema: Optional[Union[McpToolInputSchema, Dict[str, Any]]] = None,
        handler: Optional[Callable[[Dict[str, Any]], Any]] = None,
    ) -> None:
        """Register a callable tool with its schema and execution callback."""
        if isinstance(input_schema, dict):
            schema = McpToolInputSchema(
                type=input_schema.get("type", "object"),
                properties=input_schema.get("properties", {}),
                required=input_schema.get("required", []),
                additionalProperties=input_schema.get("additionalProperties", False),
            )
        elif isinstance(input_schema, McpToolInputSchema):
            schema = input_schema
        else:
            schema = McpToolInputSchema()

        tool_def = McpToolDefinition(name=name, description=description, inputSchema=schema)
        self._tools[name] = tool_def
        if handler:
            self._tool_handlers[name] = handler
        logger.debug("Registered MCP tool '%s' on server '%s'", name, self.name)

    def register_resource(
        self,
        uri: str,
        name: str,
        description: Optional[str] = None,
        mime_type: str = "application/json",
        read_handler: Optional[Callable[[str], Any]] = None,
    ) -> None:
        """Register a readable resource."""
        res = McpResource(uri=uri, name=name, description=description, mimeType=mime_type)
        self._resources[uri] = res
        if read_handler:
            self._resource_handlers[uri] = read_handler
        logger.debug("Registered MCP resource '%s' on server '%s'", uri, self.name)

    def handle_request(self, request_data: Union[str, Dict[str, Any], McpRequest]) -> McpResponse:
        """Process an incoming JSON-RPC 2.0 request and return a standard McpResponse."""
        if isinstance(request_data, str):
            try:
                data = json.loads(request_data)
            except Exception as parse_err:
                return McpResponse.error_response(
                    id=None,
                    code=McpErrorCode.PARSE_ERROR,
                    message=f"Parse error: {parse_err}",
                )
            req = McpRequest.from_dict(data)
        elif isinstance(request_data, dict):
            req = McpRequest.from_dict(request_data)
        elif isinstance(request_data, McpRequest):
            req = request_data
        else:
            return McpResponse.error_response(
                id=None,
                code=McpErrorCode.INVALID_REQUEST,
                message="Invalid request type",
            )

        req_id = req.id
        method = req.method
        params = req.params or {}

        # Protocol version validation if request metadata is supplied
        if req.metadata and req.metadata.protocol_version not in ("2026-07-28", "2024-11-05"):
            return McpResponse.error_response(
                id=req_id,
                code=McpErrorCode.UNSUPPORTED_PROTOCOL_VERSION,
                message=f"Unsupported MCP protocol version: {req.metadata.protocol_version}",
                data={
                    "supported": ["2026-07-28", "2024-11-05"],
                    "requested": req.metadata.protocol_version,
                },
            )

        is_modern_2026 = (req.metadata is None or req.metadata.protocol_version == "2026-07-28")

        try:
            if method in ("server/discover", "discover"):
                return self._handle_server_discover(req_id, params, req.metadata)
            elif method == "initialize":
                if is_modern_2026:
                    return McpResponse.error_response(
                        id=req_id,
                        code=McpErrorCode.METHOD_NOT_FOUND,
                        message="Method 'initialize' is removed in MCP 2026-07-28; use 'server/discover'",
                    )
                return self._handle_initialize(req_id, params)
            elif method == "ping":
                if is_modern_2026:
                    return McpResponse.error_response(
                        id=req_id,
                        code=McpErrorCode.METHOD_NOT_FOUND,
                        message="Method 'ping' is removed in MCP 2026-07-28",
                    )
                return McpResponse.success(req_id, {})
            elif method == "tools/list":
                return self._handle_tools_list(req_id, params)
            elif method == "tools/call":
                return self._handle_tools_call(req_id, params, req.metadata)
            elif method == "mrtr/step":
                return self._handle_mrtr_step(req_id, params, req.metadata)
            elif method == "resources/list":
                return self._handle_resources_list(req_id, params)
            elif method == "resources/read":
                return self._handle_resources_read(req_id, params)
            else:
                return McpResponse.error_response(
                    id=req_id,
                    code=McpErrorCode.METHOD_NOT_FOUND,
                    message=f"Method '{method}' not found",
                )
        except Exception as e:
            logger.exception("Internal error executing MCP method '%s'", method)
            return McpResponse.error_response(
                id=req_id,
                code=McpErrorCode.INTERNAL_ERROR,
                message=f"Internal error: {str(e)}",
            )

    def _handle_server_discover(
        self,
        req_id: Optional[Union[str, int]],
        params: Dict[str, Any],
        metadata: Optional[McpRequestMetadata] = None,
    ) -> McpResponse:
        """MCP 2026-07-28 stateless server discovery."""
        result = {
            "resultType": "complete",
            "protocolVersion": "2026-07-28",
            "supportedVersions": ["2026-07-28", "2024-11-05"],
            "serverInfo": {
                "name": self.name,
                "version": self.version,
            },
            "capabilities": self.capabilities,
            "_meta": {
                "io.modelcontextprotocol/serverInfo": {
                    "name": self.name,
                    "version": self.version,
                }
            },
            "instructions": f"Stateless MCP server '{self.name}' providing ULTRONE tools and resources.",
            "ttlMs": 3600000,
            "cacheScope": "public",
        }
        return McpResponse.success(req_id, result)

    def _handle_initialize(self, req_id: Optional[Union[str, int]], params: Dict[str, Any]) -> McpResponse:
        result = {
            "protocolVersion": "2024-11-05",
            "capabilities": self.capabilities,
            "serverInfo": {
                "name": self.name,
                "version": self.version,
            },
        }
        return McpResponse.success(req_id, result)

    def _handle_tools_list(self, req_id: Optional[Union[str, int]], params: Dict[str, Any]) -> McpResponse:
        # Deterministic sorting: alphabetical by tool name
        sorted_tools = sorted(self._tools.values(), key=lambda t: t.name)
        tools_payload = [tool.to_dict() for tool in sorted_tools]
        return McpResponse.success(
            req_id,
            {
                "resultType": "complete",
                "tools": tools_payload,
                "ttlMs": 300000,
                "cacheScope": "public",
            },
        )

    def _handle_tools_call(
        self,
        req_id: Optional[Union[str, int]],
        params: Dict[str, Any],
        metadata: Optional[McpRequestMetadata] = None,
    ) -> McpResponse:
        # Check for MRTR continuation token
        round_trip_token = params.get("roundTripToken") or (metadata.round_trip_token if metadata else None)
        if round_trip_token:
            if round_trip_token not in self._mrtr_sessions:
                return McpResponse.error_response(
                    id=req_id,
                    code=McpErrorCode.INVALID_PARAMS,
                    message=f"MRTR session not found for roundTripToken: '{round_trip_token}'",
                )
            session = self._mrtr_sessions[round_trip_token]

            # Replay protection
            if session.get("completed", False):
                return McpResponse.error_response(
                    id=req_id,
                    code=McpErrorCode.INVALID_PARAMS,
                    message=f"MRTR token '{round_trip_token}' already completed (replay rejected)",
                )

            # Expiration check
            if time.time() > session.get("expires_at", 0):
                return McpResponse.error_response(
                    id=req_id,
                    code=McpErrorCode.REQUEST_TIMEOUT,
                    message=f"MRTR token '{round_trip_token}' has expired",
                )

            # Client binding check
            caller_client = metadata.client_info.get("name") if metadata and metadata.client_info else None
            if caller_client and session.get("client_id") and caller_client != session["client_id"]:
                return McpResponse.error_response(
                    id=req_id,
                    code=McpErrorCode.UNAUTHORIZED,
                    message=f"MRTR token client mismatch: issued to '{session['client_id']}' but caller is '{caller_client}'",
                )

            # Input responses validation
            raw_responses = params.get("inputResponses") or (metadata.input_responses if metadata else None) or []
            if not raw_responses:
                return McpResponse.error_response(
                    id=req_id,
                    code=McpErrorCode.INVALID_PARAMS,
                    message="Missing required inputResponses for MRTR resumption",
                )

            seen_ids = set()
            for resp in raw_responses:
                r_id = resp.get("id") if isinstance(resp, dict) else getattr(resp, "id", None)
                if not r_id:
                    continue
                if r_id in seen_ids:
                    return McpResponse.error_response(
                        id=req_id,
                        code=McpErrorCode.INVALID_PARAMS,
                        message=f"Duplicate inputResponse ID: '{r_id}'",
                    )
                seen_ids.add(r_id)

            req_ids = {
                r.get("id") if isinstance(r, dict) else getattr(r, "id", None)
                for r in session.get("input_requests", [])
            }
            for r_id in seen_ids:
                if req_ids and r_id not in req_ids:
                    return McpResponse.error_response(
                        id=req_id,
                        code=McpErrorCode.INVALID_PARAMS,
                        message=f"Response ID '{r_id}' was not requested in MRTR session",
                    )

            # Mark session as completed
            session["completed"] = True

            # Merge arguments and execute handler
            merged_args = dict(session.get("arguments", {}))
            for resp in raw_responses:
                if isinstance(resp, dict):
                    merged_args[resp["id"]] = resp.get("value")
                else:
                    merged_args[resp.id] = resp.value

            handler = self._tool_handlers.get(session["tool_name"])
            if not handler:
                return McpResponse.success(req_id, {"resultType": "complete", "content": [{"type": "text", "text": "OK"}]})

            try:
                raw_out = handler(merged_args)
                if isinstance(raw_out, McpToolResult):
                    res_dict = raw_out.to_dict()
                    res_dict["resultType"] = "complete"
                    return McpResponse.success(req_id, res_dict)
                elif isinstance(raw_out, dict):
                    raw_out["resultType"] = "complete"
                    return McpResponse.success(req_id, raw_out)
                else:
                    res = McpToolResult.success(raw_out).to_dict()
                    res["resultType"] = "complete"
                    return McpResponse.success(req_id, res)
            except Exception as exc:
                return McpResponse.success(req_id, McpToolResult.error(str(exc)).to_dict())

        # Standard tool execution
        tool_name = params.get("name")
        if not tool_name or tool_name not in self._tools:
            return McpResponse.error_response(
                id=req_id,
                code=McpErrorCode.INVALID_PARAMS,
                message=f"Unknown tool: '{tool_name}'",
            )

        tool_def = self._tools[tool_name]
        arguments = params.get("arguments", {})

        # Validate required arguments
        schema = tool_def.inputSchema
        required_fields = schema.required if isinstance(schema, McpToolInputSchema) else schema.get("required", [])
        for field in required_fields:
            if field not in arguments:
                err_result = McpToolResult.error(f"Missing required parameter '{field}' for tool '{tool_name}'")
                return McpResponse.success(req_id, err_result.to_dict())

        handler = self._tool_handlers.get(tool_name)
        if not handler:
            err_result = McpToolResult.error(f"No handler registered for tool '{tool_name}'")
            return McpResponse.success(req_id, err_result.to_dict())

        try:
            raw_out = handler(arguments)
            # Handle interactive / multi-round-trip return
            if isinstance(raw_out, McpMrtrResult):
                client_id = metadata.client_info.get("name", "anonymous") if metadata else "anonymous"
                token = self.create_mrtr_session(client_id, tool_name, arguments, raw_out.inputRequests, raw_out.ttlMs)
                raw_out.roundTripToken = token
                return McpResponse.success(req_id, raw_out.to_dict())
            elif isinstance(raw_out, dict) and raw_out.get("resultType") == "input_required":
                client_id = metadata.client_info.get("name", "anonymous") if metadata else "anonymous"
                ttl = raw_out.get("ttlMs", 60000)
                token = self.create_mrtr_session(client_id, tool_name, arguments, raw_out.get("inputRequests", []), ttl)
                raw_out["roundTripToken"] = token
                return McpResponse.success(req_id, raw_out)
            elif isinstance(raw_out, McpToolResult):
                res_dict = raw_out.to_dict()
                res_dict["resultType"] = "complete"
                return McpResponse.success(req_id, res_dict)
            elif isinstance(raw_out, dict) and "content" in raw_out:
                raw_out["resultType"] = "complete"
                return McpResponse.success(req_id, raw_out)
            else:
                success_result = McpToolResult.success(raw_out).to_dict()
                success_result["resultType"] = "complete"
                return McpResponse.success(req_id, success_result)
        except Exception as exc:
            logger.warning("Tool execution error in '%s': %s", tool_name, exc)
            return McpResponse.success(req_id, McpToolResult.error(str(exc)).to_dict())

    def _handle_mrtr_step(
        self,
        req_id: Optional[Union[str, int]],
        params: Dict[str, Any],
        metadata: Optional[McpRequestMetadata] = None,
    ) -> McpResponse:
        """Handle Multi Round-Trip Request (MRTR) step or continuation."""
        token = params.get("round_trip_token") or (metadata.round_trip_token if metadata else None)
        if not token:
            return McpResponse.error_response(
                id=req_id,
                code=McpErrorCode.INVALID_PARAMS,
                message="MRTR step missing required 'round_trip_token'",
            )
        step_input = params.get("input", {})
        return McpResponse.success(req_id, {
            "resultType": "complete",
            "status": "mrtr_completed",
            "roundTripToken": token,
            "result": {"received_input": step_input, "status": "processed"},
        })

    def _handle_resources_list(self, req_id: Optional[Union[str, int]], params: Dict[str, Any]) -> McpResponse:
        # Deterministic sorting: by uri
        sorted_resources = sorted(self._resources.values(), key=lambda r: r.uri)
        resources_payload = [res.to_dict() for res in sorted_resources]
        return McpResponse.success(
            req_id,
            {
                "resultType": "complete",
                "resources": resources_payload,
                "ttlMs": 300000,
                "cacheScope": "public",
            },
        )

    def _handle_resources_read(self, req_id: Optional[Union[str, int]], params: Dict[str, Any]) -> McpResponse:
        uri = params.get("uri")
        if not uri or uri not in self._resources:
            return McpResponse.error_response(
                id=req_id,
                code=McpErrorCode.RESOURCE_NOT_FOUND,
                message=f"Resource not found: '{uri}'",
            )

        res_def = self._resources[uri]
        handler = self._resource_handlers.get(uri)
        content_text = ""
        if handler:
            raw = handler(uri)
            content_text = raw if isinstance(raw, str) else json.dumps(raw)
        else:
            content_text = json.dumps({"uri": uri, "name": res_def.name})

        result = {
            "resultType": "complete",
            "ttlMs": 300000,
            "cacheScope": "public",
            "contents": [
                {
                    "uri": uri,
                    "mimeType": res_def.mimeType,
                    "text": content_text,
                }
            ],
        }
        return McpResponse.success(req_id, result)


def validate_http_transport_headers(
    headers: Dict[str, str],
    method: str,
    tool_name: Optional[str] = None,
) -> Tuple[bool, Optional[int], Optional[str], int]:
    """Validate Streamable HTTP headers according to MCP 2026-07-28.

    Requires:
      MCP-Protocol-Version: 2026-07-28
      Mcp-Method: <method>
      Mcp-Name: <tool_name> (if tool_name is specified)

    Returns:
      (is_valid, error_code, error_message, http_status_code)
    """
    norm = {k.lower(): v for k, v in headers.items()}
    proto = norm.get("mcp-protocol-version")
    if not proto or proto != "2026-07-28":
        return (
            False,
            McpErrorCode.UNSUPPORTED_PROTOCOL_VERSION,
            f"Unsupported or missing MCP-Protocol-Version header: '{proto}'",
            400,
        )

    mcp_method = norm.get("mcp-method")
    if not mcp_method or mcp_method != method:
        return (
            False,
            McpErrorCode.HEADER_MISMATCH,
            f"Header Mcp-Method '{mcp_method}' does not match body JSON-RPC method '{method}'",
            400,
        )

    mcp_name = norm.get("mcp-name")
    if tool_name is not None and mcp_name is not None and mcp_name != tool_name:
        return (
            False,
            McpErrorCode.HEADER_MISMATCH,
            f"Header Mcp-Name '{mcp_name}' does not match target tool name '{tool_name}'",
            400,
        )

    return (True, None, None, 200)
