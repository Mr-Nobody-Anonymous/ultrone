"""MCP 2026-07-28 Conformance: 03_header_validation.

Spec Reference:
https://github.com/modelcontextprotocol/modelcontextprotocol/blob/main/blog/content/posts/2026-07-28-spec-ga/index.md
https://github.com/modelcontextprotocol/modelcontextprotocol/blob/main/schema/2026-07-28/schema.ts

Expected HTTP Headers:
MCP-Protocol-Version: 2026-07-28
Mcp-Method: <method>
Mcp-Name: <tool_or_resource_name>

Conditions Tested:
1. Valid headers pass with HTTP 200.
2. Protocol version header missing or unsupported -> HTTP 400, code -32022.
3. Method header mismatch -> HTTP 400, code -32023.
4. Name header mismatch -> HTTP 400, code -32023.
"""

import pytest
from packages.agents.mcp.protocol import McpErrorCode
from packages.agents.mcp.server import validate_http_transport_headers


def test_http_headers_valid_match():
    headers = {
        "Content-Type": "application/json",
        "MCP-Protocol-Version": "2026-07-28",
        "Mcp-Method": "tools/call",
        "Mcp-Name": "fire_interceptor",
    }
    valid, code, msg, status = validate_http_transport_headers(
        headers, method="tools/call", tool_name="fire_interceptor"
    )
    assert valid is True
    assert status == 200
    assert code is None


def test_http_headers_unsupported_protocol_version():
    headers = {
        "Content-Type": "application/json",
        "MCP-Protocol-Version": "1999-01-01",
        "Mcp-Method": "tools/call",
        "Mcp-Name": "fire_interceptor",
    }
    valid, code, msg, status = validate_http_transport_headers(
        headers, method="tools/call", tool_name="fire_interceptor"
    )
    assert valid is False
    assert status == 400
    assert code == McpErrorCode.UNSUPPORTED_PROTOCOL_VERSION
    assert code == -32022


def test_http_headers_method_mismatch():
    headers = {
        "Content-Type": "application/json",
        "MCP-Protocol-Version": "2026-07-28",
        "Mcp-Method": "resources/list",  # Mismatch with actual method 'tools/call'
        "Mcp-Name": "fire_interceptor",
    }
    valid, code, msg, status = validate_http_transport_headers(
        headers, method="tools/call", tool_name="fire_interceptor"
    )
    assert valid is False
    assert status == 400
    assert code == McpErrorCode.HEADER_MISMATCH
    assert code == -32023


def test_http_headers_name_mismatch():
    headers = {
        "Content-Type": "application/json",
        "MCP-Protocol-Version": "2026-07-28",
        "Mcp-Method": "tools/call",
        "Mcp-Name": "radar_scan",  # Mismatch with body tool name 'fire_interceptor'
    }
    valid, code, msg, status = validate_http_transport_headers(
        headers, method="tools/call", tool_name="fire_interceptor"
    )
    assert valid is False
    assert status == 400
    assert code == McpErrorCode.HEADER_MISMATCH
    assert code == -32023
