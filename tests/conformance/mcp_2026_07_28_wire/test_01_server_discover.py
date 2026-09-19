"""MCP 2026-07-28 Conformance: 01_server_discover.

Spec Reference:
https://github.com/modelcontextprotocol/modelcontextprotocol/blob/main/docs/specification/2026-07-28/server/discover.mdx

Expected Request:
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "server/discover",
  "params": {}
}

Expected Response:
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "resultType": "complete",
    "supportedVersions": ["2026-07-28", ...],
    "capabilities": {...},
    "_meta": {
      "io.modelcontextprotocol/serverInfo": {
        "name": "...",
        "version": "..."
      }
    },
    "instructions": "...",
    "ttlMs": 3600000,
    "cacheScope": "public"
  }
}
"""

import pytest
from packages.agents.mcp.protocol import McpRequest
from packages.agents.mcp.server import McpServer


def test_server_discover_exact_2026_wire_schema():
    server = McpServer(name="ultrone-radar-mcp", version="2.0.0")
    req = McpRequest(id=1, method="server/discover", params={})
    resp = server.handle_request(req)

    assert resp.error is None
    result = resp.result
    assert result is not None

    # Wire schema assertions:
    assert result["resultType"] == "complete", "Must return resultType: 'complete'"
    assert "supportedVersions" in result, "Wire field must be 'supportedVersions', not 'supportedProtocolVersions'"
    assert "2026-07-28" in result["supportedVersions"]
    assert "capabilities" in result and isinstance(result["capabilities"], dict)
    assert "_meta" in result and "io.modelcontextprotocol/serverInfo" in result["_meta"]
    server_info = result["_meta"]["io.modelcontextprotocol/serverInfo"]
    assert server_info["name"] == "ultrone-radar-mcp"
    assert server_info["version"] == "2.0.0"
    assert "instructions" in result
    assert result["ttlMs"] == 3600000
    assert result["cacheScope"] == "public"
