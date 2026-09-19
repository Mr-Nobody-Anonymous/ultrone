"""MCP 2026-07-28 Conformance: 06_resources.

Spec Reference:
https://github.com/modelcontextprotocol/modelcontextprotocol/blob/main/blog/content/posts/2026-07-28-spec-ga/index.md

Requirements:
1. resources/list has ttlMs, cacheScope, resultType: "complete"
2. resources/read has ttlMs, cacheScope, resultType: "complete"
3. Resource list has deterministic ordering.
"""

import json
import pytest
from packages.agents.mcp.protocol import McpErrorCode, McpRequest, McpRequestMetadata
from packages.agents.mcp.server import McpServer


@pytest.fixture
def resource_server():
    server = McpServer(name="telemetry-mcp", version="1.0.0")
    # Register in non-alphabetical URI order
    server.register_resource("telemetry://drone/99", "Drone 99 Telemetry", read_handler=lambda uri: {"battery": 88})
    server.register_resource("telemetry://drone/01", "Drone 01 Telemetry", read_handler=lambda uri: {"battery": 95})
    server.register_resource("telemetry://drone/50", "Drone 50 Telemetry", read_handler=lambda uri: {"battery": 42})
    return server


def test_resources_list_has_cache_metadata(resource_server):
    req = McpRequest(id=30, method="resources/list", params={}, metadata=McpRequestMetadata(protocol_version="2026-07-28"))
    resp = resource_server.handle_request(req)

    assert resp.error is None
    result = resp.result
    assert result["resultType"] == "complete"
    assert "ttlMs" in result and result["ttlMs"] > 0
    assert result["cacheScope"] == "public"
    assert "resources" in result

    # Deterministic sorting check: URIs sorted alphabetically
    uris = [r["uri"] for r in result["resources"]]
    assert uris == ["telemetry://drone/01", "telemetry://drone/50", "telemetry://drone/99"]


def test_resources_read_has_cache_metadata(resource_server):
    req = McpRequest(
        id=31,
        method="resources/read",
        params={"uri": "telemetry://drone/01"},
        metadata=McpRequestMetadata(protocol_version="2026-07-28"),
    )
    resp = resource_server.handle_request(req)

    assert resp.error is None
    result = resp.result
    assert result["resultType"] == "complete"
    assert result["ttlMs"] == 300000
    assert result["cacheScope"] == "public"
    assert "contents" in result
    assert len(result["contents"]) == 1
    content_item = result["contents"][0]
    assert content_item["uri"] == "telemetry://drone/01"
    parsed = json.loads(content_item["text"])
    assert parsed["battery"] == 95


def test_resources_read_not_found(resource_server):
    req = McpRequest(
        id=32,
        method="resources/read",
        params={"uri": "telemetry://drone/nonexistent"},
        metadata=McpRequestMetadata(protocol_version="2026-07-28"),
    )
    resp = resource_server.handle_request(req)

    assert resp.error is not None
    assert resp.error["code"] == McpErrorCode.RESOURCE_NOT_FOUND
    assert resp.error["code"] == -32002
