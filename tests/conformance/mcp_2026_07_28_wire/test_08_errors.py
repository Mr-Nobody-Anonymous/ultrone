"""MCP 2026-07-28 Conformance: 08_errors.

Spec Reference:
https://github.com/modelcontextprotocol/modelcontextprotocol/blob/main/schema/2026-07-28/schema.ts

Verifies official error codes across JSON-RPC and MCP 2026-07-28.
"""

import pytest
from packages.agents.mcp.protocol import McpErrorCode, McpRequest, McpRequestMetadata
from packages.agents.mcp.server import McpServer


@pytest.fixture
def test_server():
    server = McpServer(name="error-test-server", version="1.0.0")
    server.register_tool(
        name="divide",
        description="Divide numbers",
        handler=lambda args: {"res": args["a"] / args["b"]},
    )
    return server


def test_parse_error_code(test_server):
    resp = test_server.handle_request("{malformed_json_here")
    assert resp.error is not None
    assert resp.error["code"] == McpErrorCode.PARSE_ERROR
    assert resp.error["code"] == -32700


def test_invalid_request_code(test_server):
    resp = test_server.handle_request(12345)  # Invalid request type
    assert resp.error is not None
    assert resp.error["code"] == McpErrorCode.INVALID_REQUEST
    assert resp.error["code"] == -32600


def test_method_not_found_code(test_server):
    req = McpRequest(id=1, method="non_existent_rpc_method", params={})
    resp = test_server.handle_request(req)
    assert resp.error is not None
    assert resp.error["code"] == McpErrorCode.METHOD_NOT_FOUND
    assert resp.error["code"] == -32601


def test_unsupported_protocol_version_code(test_server):
    req = McpRequest(
        id=2,
        method="tools/list",
        metadata=McpRequestMetadata(protocol_version="2021-01-01"),
    )
    resp = test_server.handle_request(req)
    assert resp.error is not None
    assert resp.error["code"] == McpErrorCode.UNSUPPORTED_PROTOCOL_VERSION
    assert resp.error["code"] == -32022
