# Copyright (c) Ultrone Contributors. All rights reserved.
"""Model Context Protocol (MCP) JSON-RPC 2.0 schema and data models.

Complies with the Anthropic Model Context Protocol specification:
https://spec.modelcontextprotocol.io/
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Union


class McpErrorCode(int, Enum):
    """Standard JSON-RPC 2.0 and MCP 2026-07-28 error codes."""

    PARSE_ERROR = -32700
    INVALID_REQUEST = -32600
    METHOD_NOT_FOUND = -32601
    INVALID_PARAMS = -32602
    INTERNAL_ERROR = -32603
    RESOURCE_NOT_FOUND = -32002
    TOOL_EXECUTION_ERROR = -32000
    UNSUPPORTED_PROTOCOL_VERSION = -32022
    PROTOCOL_VERSION_MISMATCH = -32022  # Alias for backward compatibility
    HEADER_MISMATCH = -32023
    UNAUTHORIZED = -32003
    ROUND_TRIP_REQUIRED = -32004
    REQUEST_TIMEOUT = -32005


@dataclass
class McpToolInputSchema:
    """JSON Schema defining arguments for an MCP tool."""

    type: str = "object"
    properties: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    required: List[str] = field(default_factory=list)
    additionalProperties: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.type,
            "properties": self.properties,
            "required": self.required,
            "additionalProperties": self.additionalProperties,
        }


@dataclass
class McpToolDefinition:
    """Metadata describing an MCP tool callable by language models."""

    name: str
    description: str
    inputSchema: McpToolInputSchema = field(default_factory=McpToolInputSchema)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "inputSchema": self.inputSchema.to_dict() if isinstance(self.inputSchema, McpToolInputSchema) else self.inputSchema,
        }


@dataclass
class McpResource:
    """A contextual data source readable via MCP."""

    uri: str
    name: str
    description: Optional[str] = None
    mimeType: str = "application/json"

    def to_dict(self) -> Dict[str, Any]:
        d = {"uri": self.uri, "name": self.name, "mimeType": self.mimeType}
        if self.description:
            d["description"] = self.description
        return d


@dataclass
class McpTextContent:
    """Standard text content block in an MCP tool response."""

    type: str = "text"
    text: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {"type": self.type, "text": self.text}


@dataclass
class McpToolResult:
    """Result returned from an MCP tools/call invocation."""

    content: List[McpTextContent] = field(default_factory=list)
    isError: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "content": [c.to_dict() if hasattr(c, "to_dict") else c for c in self.content],
            "isError": self.isError,
        }

    @classmethod
    def success(cls, data: Union[str, Dict[str, Any]]) -> McpToolResult:
        text = data if isinstance(data, str) else json.dumps(data, indent=2)
        return cls(content=[McpTextContent(type="text", text=text)], isError=False)

    @classmethod
    def error(cls, message: str) -> McpToolResult:
        return cls(
            content=[McpTextContent(type="text", text=json.dumps({"error": message}))],
            isError=True,
        )


@dataclass
class McpInputRequest:
    """An input request issued by server during an MRTR exchange."""
    id: str
    type: str = "string"  # string, number, boolean, object
    description: Optional[str] = None
    default: Any = None

    def to_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {"id": self.id, "type": self.type}
        if self.description:
            d["description"] = self.description
        if self.default is not None:
            d["default"] = self.default
        return d


@dataclass
class McpInputResponse:
    """Client response to an MRTR input request."""
    id: str
    value: Any

    def to_dict(self) -> Dict[str, Any]:
        return {"id": self.id, "value": self.value}


@dataclass
class McpMrtrResult:
    """Wire representation of an MRTR intermediate result."""
    roundTripToken: str
    inputRequests: List[McpInputRequest] = field(default_factory=list)
    resultType: str = "input_required"
    ttlMs: int = 60000

    def to_dict(self) -> Dict[str, Any]:
        return {
            "resultType": self.resultType,
            "roundTripToken": self.roundTripToken,
            "inputRequests": [r.to_dict() for r in self.inputRequests],
            "ttlMs": self.ttlMs,
        }


@dataclass
class McpRequestMetadata:
    """MCP 2026-07-28 request metadata travelling per-request."""
    protocol_version: str = "2026-07-28"
    client_info: Dict[str, Any] = field(default_factory=dict)
    capabilities: Dict[str, Any] = field(default_factory=dict)
    round_trip_token: Optional[str] = None
    input_responses: Optional[List[Dict[str, Any]]] = None

    def to_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {
            "protocolVersion": self.protocol_version,
            "clientInfo": self.client_info,
            "capabilities": self.capabilities,
        }
        if self.round_trip_token is not None:
            d["roundTripToken"] = self.round_trip_token
        if self.input_responses is not None:
            d["inputResponses"] = self.input_responses
        return d

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> McpRequestMetadata:
        return cls(
            protocol_version=data.get("protocolVersion", "2026-07-28"),
            client_info=data.get("clientInfo", {}),
            capabilities=data.get("capabilities", {}),
            round_trip_token=data.get("roundTripToken"),
            input_responses=data.get("inputResponses"),
        )


@dataclass
class McpRequest:
    """JSON-RPC 2.0 Request conforming to MCP 2026-07-28 stateless core."""

    method: str
    params: Optional[Dict[str, Any]] = None
    id: Optional[Union[str, int]] = None
    jsonrpc: str = "2.0"
    metadata: Optional[McpRequestMetadata] = None

    def to_dict(self) -> Dict[str, Any]:
        res: Dict[str, Any] = {"jsonrpc": self.jsonrpc, "method": self.method}
        if self.params is not None:
            res["params"] = self.params
        if self.id is not None:
            res["id"] = self.id
        if self.metadata is not None:
            res["metadata"] = self.metadata.to_dict()
        return res

    def to_json(self) -> str:
        return json.dumps(self.to_dict())

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> McpRequest:
        meta = None
        if "metadata" in data and isinstance(data["metadata"], dict):
            meta = McpRequestMetadata.from_dict(data["metadata"])
        return cls(
            method=data.get("method", ""),
            params=data.get("params"),
            id=data.get("id"),
            jsonrpc=data.get("jsonrpc", "2.0"),
            metadata=meta,
        )


@dataclass
class McpResponse:
    """JSON-RPC 2.0 Response."""

    id: Optional[Union[str, int]]
    result: Optional[Dict[str, Any]] = None
    error: Optional[Dict[str, Any]] = None
    jsonrpc: str = "2.0"

    def to_dict(self) -> Dict[str, Any]:
        res: Dict[str, Any] = {"jsonrpc": self.jsonrpc, "id": self.id}
        if self.error is not None:
            res["error"] = self.error
        else:
            res["result"] = self.result or {}
        return res

    def to_json(self) -> str:
        return json.dumps(self.to_dict())

    @classmethod
    def success(cls, id: Optional[Union[str, int]], result: Dict[str, Any]) -> McpResponse:
        return cls(id=id, result=result)

    @classmethod
    def error_response(
        cls, id: Optional[Union[str, int]], code: int, message: str, data: Optional[Any] = None
    ) -> McpResponse:
        err: Dict[str, Any] = {"code": code, "message": message}
        if data is not None:
            err["data"] = data
        return cls(id=id, error=err)
