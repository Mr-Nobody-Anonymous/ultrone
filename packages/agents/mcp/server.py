# Copyright (c) Ultrone Contributors. All rights reserved.
"""McpServer: Server implementation exposing tools and resources via MCP JSON-RPC 2.0."""

from __future__ import annotations

import json
import logging
from typing import Any, Callable, Dict, List, Optional, Union

from .protocol import (
    McpErrorCode,
    McpRequest,
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

        try:
            if method == "initialize":
                return self._handle_initialize(req_id, params)
            elif method == "ping":
                return McpResponse.success(req_id, {})
            elif method == "tools/list":
                return self._handle_tools_list(req_id, params)
            elif method == "tools/call":
                return self._handle_tools_call(req_id, params)
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
        tools_payload = [tool.to_dict() for tool in self._tools.values()]
        return McpResponse.success(req_id, {"tools": tools_payload})

    def _handle_tools_call(self, req_id: Optional[Union[str, int]], params: Dict[str, Any]) -> McpResponse:
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
            if isinstance(raw_out, McpToolResult):
                return McpResponse.success(req_id, raw_out.to_dict())
            elif isinstance(raw_out, dict) and "content" in raw_out:
                return McpResponse.success(req_id, raw_out)
            else:
                success_result = McpToolResult.success(raw_out)
                return McpResponse.success(req_id, success_result.to_dict())
        except Exception as exc:
            logger.warning("Tool execution error in '%s': %s", tool_name, exc)
            return McpResponse.success(req_id, McpToolResult.error(str(exc)).to_dict())

    def _handle_resources_list(self, req_id: Optional[Union[str, int]], params: Dict[str, Any]) -> McpResponse:
        resources_payload = [res.to_dict() for res in self._resources.values()]
        return McpResponse.success(req_id, {"resources": resources_payload})

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
            "contents": [
                {
                    "uri": uri,
                    "mimeType": res_def.mimeType,
                    "text": content_text,
                }
            ]
        }
        return McpResponse.success(req_id, result)
