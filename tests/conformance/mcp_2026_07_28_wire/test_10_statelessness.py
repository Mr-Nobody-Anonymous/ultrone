"""MCP 2026-07-28 Conformance: 10_statelessness.

Spec Reference:
https://github.com/modelcontextprotocol/modelcontextprotocol/blob/main/blog/content/posts/2026-07-28-spec-ga/index.md

Verifies that the server core requires no session ID (Mcp-Session-Id) or mandatory handshake state.
"""

import pytest
from packages.agents.mcp.protocol import McpRequest, McpRequestMetadata
from packages.agents.mcp.server import McpServer


def test_independent_stateless_invocations():
    server = McpServer(name="stateless-server", version="1.0.0")
    server.register_tool("add", "Add two numbers", handler=lambda args: {"sum": args["a"] + args["b"]})

    # Call directly without prior initialization or session ID
    req1 = McpRequest(
        id="call-1",
        method="tools/call",
        params={"name": "add", "arguments": {"a": 10, "b": 20}},
        metadata=McpRequestMetadata(protocol_version="2026-07-28", client_info={"name": "client-1"}),
    )
    res1 = server.handle_request(req1)
    assert res1.error is None
    assert "30" in res1.result["content"][0]["text"]

    # Completely different client on the same server instance
    req2 = McpRequest(
        id="call-2",
        method="tools/call",
        params={"name": "add", "arguments": {"a": 100, "b": 200}},
        metadata=McpRequestMetadata(protocol_version="2026-07-28", client_info={"name": "client-2"}),
    )
    res2 = server.handle_request(req2)
    assert res2.error is None
    assert "300" in res2.result["content"][0]["text"]
