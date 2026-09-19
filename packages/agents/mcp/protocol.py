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
    """Standard JSON-RPC 2.0 and MCP error codes."""

    PARSE_ERROR = -32700
    INVALID_REQUEST = -32600
    METHOD_NOT_FOUND = -32601
    INVALID_PARAMS = -32602
    INTERNAL_ERROR = -32603
    RESOURCE_NOT_FOUND = -32002
    TOOL_EXECUTION_ERROR = -32000


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
class McpRequest:
    """JSON-RPC 2.0 Request."""

    method: str
    params: Optional[Dict[str, Any]] = None
    id: Optional[Union[str, int]] = None
    jsonrpc: str = "2.0"

    def to_dict(self) -> Dict[str, Any]:
        res: Dict[str, Any] = {"jsonrpc": self.jsonrpc, "method": self.method}
        if self.params is not None:
            res["params"] = self.params
        if self.id is not None:
            res["id"] = self.id
        return res

    def to_json(self) -> str:
        return json.dumps(self.to_dict())

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> McpRequest:
        return cls(
            method=data.get("method", ""),
            params=data.get("params"),
            id=data.get("id"),
            jsonrpc=data.get("jsonrpc", "2.0"),
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
