"""MCP 2026-07-28 Conformance: 02_protocol_version.

Spec Reference:
https://github.com/modelcontextprotocol/modelcontextprotocol/blob/main/schema/2026-07-28/schema.ts

Expected Error:
-32022 = UNSUPPORTED_PROTOCOL_VERSION
Data payload:
{
  "supported": ["2026-07-28", ...],
  "requested": "..."
}
"""

import pytest
from packages.agents.mcp.protocol import McpErrorCode, McpRequest, McpRequestMetadata
from packages.agents.mcp.server import McpServer


def test_unsupported_protocol_version_wire_error():
    server = McpServer(name="ultrone-server", version="1.0.0")
    req = McpRequest(
        id=99,
        method="tools/list",
        params={},
        metadata=McpRequestMetadata(protocol_version="2023-01-01"),
    )
    resp = server.handle_request(req)

    assert resp.error is not None
    assert resp.error["code"] == -32022
    assert resp.error["code"] == McpErrorCode.UNSUPPORTED_PROTOCOL_VERSION
    assert "data" in resp.error
    assert "2026-07-28" in resp.error["data"]["supported"]
    assert resp.error["data"]["requested"] == "2023-01-01"
