"""MCP 2026-07-28 Conformance: 04_tools_call.

Spec Reference:
https://github.com/modelcontextprotocol/modelcontextprotocol/blob/main/docs/specification/2026-07-28/server/tools.mdx

Expected Wire Shape:
Request:
{
  "jsonrpc": "2.0",
  "id": 10,
  "method": "tools/call",
  "params": {
    "name": "calc_intercept",
    "arguments": {"azimuth": 45.0, "range_km": 120.0}
  }
}

Response (Success):
{
  "jsonrpc": "2.0",
  "id": 10,
  "result": {
    "resultType": "complete",
    "content": [
      {
        "type": "text",
        "text": "..."
      }
    ],
    "isError": false
  }
}
"""

import json
import pytest
from packages.agents.mcp.protocol import (
    McpErrorCode,
    McpRequest,
    McpRequestMetadata,
    McpToolInputSchema,
    McpToolResult,
)
from packages.agents.mcp.server import McpServer


@pytest.fixture
def server_with_tools():
    server = McpServer(name="weapons-mcp", version="1.0.0")
    server.register_tool(
        name="calc_intercept",
        description="Calculate intercept trajectory",
        input_schema=McpToolInputSchema(
            type="object",
            properties={
                "azimuth": {"type": "number"},
                "range_km": {"type": "number"},
            },
            required=["azimuth", "range_km"],
        ),
        handler=lambda args: {"eta_seconds": args["range_km"] / 1.5, "heading": args["azimuth"]},
    )
    return server


def test_tools_call_success_wire_format(server_with_tools):
    req = McpRequest(
        id=10,
        method="tools/call",
        params={"name": "calc_intercept", "arguments": {"azimuth": 45.0, "range_km": 120.0}},
        metadata=McpRequestMetadata(protocol_version="2026-07-28"),
    )
    resp = server_with_tools.handle_request(req)

    assert resp.error is None
    assert resp.result is not None
    assert resp.result["resultType"] == "complete"
    assert resp.result["isError"] is False
    assert len(resp.result["content"]) >= 1
    content_item = resp.result["content"][0]
    assert content_item["type"] == "text"
    parsed = json.loads(content_item["text"])
    assert parsed["eta_seconds"] == 80.0
    assert parsed["heading"] == 45.0


def test_tools_call_missing_required_arg(server_with_tools):
    req = McpRequest(
        id=11,
        method="tools/call",
        params={"name": "calc_intercept", "arguments": {"azimuth": 45.0}},  # Missing range_km
        metadata=McpRequestMetadata(protocol_version="2026-07-28"),
    )
    resp = server_with_tools.handle_request(req)

    assert resp.error is None  # Standard tool result with isError: true
    assert resp.result["isError"] is True
    assert "Missing required parameter 'range_km'" in resp.result["content"][0]["text"]


def test_tools_call_unknown_tool(server_with_tools):
    req = McpRequest(
        id=12,
        method="tools/call",
        params={"name": "non_existent_tool", "arguments": {}},
        metadata=McpRequestMetadata(protocol_version="2026-07-28"),
    )
    resp = server_with_tools.handle_request(req)

    assert resp.error is not None
    assert resp.error["code"] == McpErrorCode.INVALID_PARAMS
    assert "Unknown tool" in resp.error["message"]
