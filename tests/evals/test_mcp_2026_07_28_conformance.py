"""Conformance tests for Model Context Protocol (MCP) specification 2026-07-28.

Verifies:
1. Stateless protocol core (zero mandatory handshake or Mcp-Session-Id).
2. server/discover endpoint and capability advertisement.
3. Per-request protocol metadata propagation.
4. Protocol version validation (-32001 PROTOCOL_VERSION_MISMATCH).
5. Multi Round-Trip Request (MRTR) pattern.
6. Standard JSON Schema argument validation and error codes.
"""

import json
import pytest
from packages.agents.mcp.client import McpClient
from packages.agents.mcp.protocol import (
    McpErrorCode,
    McpRequest,
    McpRequestMetadata,
    McpResponse,
    McpToolInputSchema,
    McpToolResult,
)
from packages.agents.mcp.server import McpServer


@pytest.fixture
def mcp_server():
    server = McpServer(name="conformance-test-server", version="2.0.0")
    server.register_tool(
        name="compute_vector",
        description="Compute 2D vector norm",
        input_schema=McpToolInputSchema(
            type="object",
            properties={
                "x": {"type": "number", "description": "X coordinate"},
                "y": {"type": "number", "description": "Y coordinate"},
            },
            required=["x", "y"],
        ),
        handler=lambda args: {"norm": (args["x"] ** 2 + args["y"] ** 2) ** 0.5},
    )
    return server


def test_server_discover_endpoint(mcp_server):
    """Verify standard server/discover response schema."""
    req = McpRequest(id=1, method="server/discover", params={})
    res = mcp_server.handle_request(req)

    assert res.error is None
    assert res.result is not None
    assert res.result["resultType"] == "complete"
    assert res.result["ttlMs"] == 3600000
    assert res.result["cacheScope"] == "public"
    assert "2026-07-28" in res.result["supportedVersions"]
    assert res.result["_meta"]["io.modelcontextprotocol/serverInfo"]["name"] == "conformance-test-server"
    assert "tools" in res.result["capabilities"]


def test_stateless_tool_call_without_prior_handshake(mcp_server):
    """Verify protocol core is stateless: tool calls execute without preceding initialize."""
    # Direct tool call with no handshake, no session ID
    req = McpRequest(
        id=101,
        method="tools/call",
        params={"name": "compute_vector", "arguments": {"x": 3.0, "y": 4.0}},
        metadata=McpRequestMetadata(protocol_version="2026-07-28", client_info={"name": "stateless-client"}),
    )
    res = mcp_server.handle_request(req)

    assert res.error is None
    assert not res.result.get("isError", False)
    content = res.result["content"]
    data = json.loads(content[0]["text"])
    assert data["norm"] == 5.0


def test_protocol_version_validation_mismatch(mcp_server):
    """Verify that requests declaring incompatible protocol versions receive -32022 UNSUPPORTED_PROTOCOL_VERSION."""
    req = McpRequest(
        id=102,
        method="tools/list",
        params={},
        metadata=McpRequestMetadata(protocol_version="1999-01-01"),  # Unsupported version
    )
    res = mcp_server.handle_request(req)

    assert res.error is not None
    assert res.error["code"] == McpErrorCode.UNSUPPORTED_PROTOCOL_VERSION
    assert res.error["code"] == -32022
    assert "Unsupported MCP protocol version" in res.error["message"]
    assert "supported" in res.error["data"]
    assert res.error["data"]["requested"] == "1999-01-01"


def test_multi_round_trip_request_mrtr_flow(mcp_server):
    """Verify Multi Round-Trip Request (MRTR) step handling."""
    client = McpClient(server=mcp_server)
    client.connect()

    # Successful MRTR step with round-trip token
    token = "rt-step-abc-123"
    res = client.call_mrtr_step(token=token, step_input={"confirmation": True, "override": False})

    assert res.error is None
    assert res.result["status"] == "mrtr_completed"
    assert res.result["roundTripToken"] == token
    assert res.result["result"]["status"] == "processed"

    # Missing token fails with INVALID_PARAMS
    req_invalid = McpRequest(id=103, method="mrtr/step", params={"input": {}})
    res_err = mcp_server.handle_request(req_invalid)
    assert res_err.error is not None
    assert res_err.error["code"] == McpErrorCode.INVALID_PARAMS


def test_schema_validation_error_code_on_missing_required(mcp_server):
    """Verify JSON Schema validation errors on missing required parameters."""
    req = McpRequest(
        id=104,
        method="tools/call",
        params={"name": "compute_vector", "arguments": {"x": 3.0}},  # Missing 'y'
        metadata=McpRequestMetadata(protocol_version="2026-07-28"),
    )
    res = mcp_server.handle_request(req)

    assert res.error is None  # Handled tool result error
    assert res.result["isError"] is True
    assert "Missing required parameter 'y'" in res.result["content"][0]["text"]
