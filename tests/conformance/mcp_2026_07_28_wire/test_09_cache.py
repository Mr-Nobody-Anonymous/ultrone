"""MCP 2026-07-28 Conformance: 09_cache.

Spec Reference:
https://github.com/modelcontextprotocol/modelcontextprotocol/blob/main/blog/content/posts/2026-07-28-spec-ga/index.md

Verifies ttlMs and cacheScope metadata across discovery, tools, and resources.
"""

import pytest
from packages.agents.mcp.protocol import McpRequest, McpRequestMetadata
from packages.agents.mcp.server import McpServer


@pytest.fixture
def caching_server():
    server = McpServer(name="cache-server", version="1.0.0")
    server.register_tool("calc_distance", "Calculate distance", handler=lambda args: {"dist": 10})
    server.register_resource("telemetry://geo/map", "Map Resource", read_handler=lambda uri: "map_data")
    return server


def test_cache_metadata_consistency_across_endpoints(caching_server):
    meta = McpRequestMetadata(protocol_version="2026-07-28")

    # 1. Discover
    r_disc = caching_server.handle_request(McpRequest(id=1, method="server/discover", params={}, metadata=meta))
    assert r_disc.error is None
    assert r_disc.result["ttlMs"] > 0
    assert r_disc.result["cacheScope"] in ("public", "session")

    # 2. Tools list
    r_tools = caching_server.handle_request(McpRequest(id=2, method="tools/list", params={}, metadata=meta))
    assert r_tools.error is None
    assert r_tools.result["ttlMs"] > 0
    assert r_tools.result["cacheScope"] in ("public", "session")

    # 3. Resources list
    r_res = caching_server.handle_request(McpRequest(id=3, method="resources/list", params={}, metadata=meta))
    assert r_res.error is None
    assert r_res.result["ttlMs"] > 0
    assert r_res.result["cacheScope"] in ("public", "session")

    # 4. Resources read
    r_read = caching_server.handle_request(McpRequest(id=4, method="resources/read", params={"uri": "telemetry://geo/map"}, metadata=meta))
    assert r_read.error is None
    assert r_read.result["ttlMs"] > 0
    assert r_read.result["cacheScope"] in ("public", "session")
