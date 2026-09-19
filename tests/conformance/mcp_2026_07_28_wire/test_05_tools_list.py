"""MCP 2026-07-28 Conformance: 05_tools_list.

Spec Reference:
https://github.com/modelcontextprotocol/modelcontextprotocol/blob/main/blog/content/posts/2026-07-28-spec-ga/index.md

Requirements:
1. Cache metadata: ttlMs and cacheScope present in list results.
2. Result type: resultType: "complete".
3. Deterministic ordering: tools returned in deterministic sorted order rather than insertion order.
"""

import pytest
from packages.agents.mcp.protocol import McpRequest, McpRequestMetadata
from packages.agents.mcp.server import McpServer


def test_tools_list_has_cache_metadata():
    server = McpServer(name="catalog-server", version="1.0.0")
    server.register_tool("radar_scan", "Scan sector")
    req = McpRequest(id=20, method="tools/list", params={}, metadata=McpRequestMetadata(protocol_version="2026-07-28"))
    resp = server.handle_request(req)

    assert resp.error is None
    result = resp.result
    assert result["resultType"] == "complete"
    assert "ttlMs" in result and result["ttlMs"] > 0
    assert result["cacheScope"] in ("public", "session")
    assert "tools" in result


def test_tool_order_is_deterministic():
    server = McpServer(name="catalog-server", version="1.0.0")
    # Register tools intentionally in reverse / arbitrary non-alphabetical order
    server.register_tool("zeta_weapon", "Zeta")
    server.register_tool("alpha_sensor", "Alpha")
    server.register_tool("gamma_tracker", "Gamma")
    server.register_tool("beta_comms", "Beta")

    req = McpRequest(id=21, method="tools/list", params={}, metadata=McpRequestMetadata(protocol_version="2026-07-28"))
    resp = server.handle_request(req)

    assert resp.error is None
    tool_names = [t["name"] for t in resp.result["tools"]]
    # Must be deterministically sorted alphabetically
    assert tool_names == ["alpha_sensor", "beta_comms", "gamma_tracker", "zeta_weapon"]
