"""MCP 2026-07-28 Conformance: 11_backward_compatibility.

Spec Reference:
https://github.com/modelcontextprotocol/modelcontextprotocol/blob/main/blog/content/posts/2026-07-28-spec-ga/index.md
https://github.com/modelcontextprotocol/modelcontextprotocol/blob/main/docs/specification/2026-07-28/changelog.mdx

Verifies:
1. test_2026_does_not_expose_ping (ping removed in 2026-07-28).
2. test_2026_does_not_expose_initialize (initialize removed in modern mode).
3. Legacy 2024-11-05 clients can still call initialize and ping via backward-compatibility era path.
4. Unsupported versions receive -32022.
"""

import pytest
from packages.agents.mcp.protocol import McpErrorCode, McpRequest, McpRequestMetadata
from packages.agents.mcp.server import McpServer


@pytest.fixture
def server():
    return McpServer(name="dual-era-server", version="1.0.0")


def test_2026_does_not_expose_ping(server):
    """MCP 2026-07-28 explicitly removed ping; must return METHOD_NOT_FOUND."""
    req = McpRequest(
        id=1,
        method="ping",
        params={},
        metadata=McpRequestMetadata(protocol_version="2026-07-28"),
    )
    resp = server.handle_request(req)

    assert resp.error is not None
    assert resp.error["code"] == McpErrorCode.METHOD_NOT_FOUND
    assert "ping" in resp.error["message"]


def test_2026_does_not_expose_initialize(server):
    """MCP 2026-07-28 removed initialize in favor of server/discover."""
    req = McpRequest(
        id=2,
        method="initialize",
        params={},
        metadata=McpRequestMetadata(protocol_version="2026-07-28"),
    )
    resp = server.handle_request(req)

    assert resp.error is not None
    assert resp.error["code"] == McpErrorCode.METHOD_NOT_FOUND
    assert "server/discover" in resp.error["message"]


def test_legacy_2024_client_compatibility_path(server):
    """Legacy 2024-11-05 requests negotiate via backward compatibility path."""
    meta_legacy = McpRequestMetadata(protocol_version="2024-11-05")

    # Legacy initialize
    req_init = McpRequest(id=3, method="initialize", params={}, metadata=meta_legacy)
    resp_init = server.handle_request(req_init)
    assert resp_init.error is None
    assert resp_init.result["protocolVersion"] == "2024-11-05"

    # Legacy ping
    req_ping = McpRequest(id=4, method="ping", params={}, metadata=meta_legacy)
    resp_ping = server.handle_request(req_ping)
    assert resp_ping.error is None


def test_unsupported_version_returns_32022(server):
    """Any unsupported version returns -32022 UNSUPPORTED_PROTOCOL_VERSION."""
    meta_unsupported = McpRequestMetadata(protocol_version="2025-06-01")
    req = McpRequest(id=5, method="server/discover", params={}, metadata=meta_unsupported)
    resp = server.handle_request(req)

    assert resp.error is not None
    assert resp.error["code"] == -32022
    assert resp.error["code"] == McpErrorCode.UNSUPPORTED_PROTOCOL_VERSION
