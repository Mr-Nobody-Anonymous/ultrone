"""MCP 2026-07-28 Conformance: 07_mrtr.

Spec Reference:
https://github.com/modelcontextprotocol/modelcontextprotocol/blob/main/blog/content/posts/2026-07-28-spec-ga/index.md

Exchange Flow:
tools/call (initial)
  ↓
Response:
  resultType: "input_required"
  roundTripToken: "mrt_..."
  inputRequests: [...]
  ttlMs: 60000
  ↓
Client retry:
tools/call (same or continuation) with:
  roundTripToken: "mrt_..."
  inputResponses: [...]
  ↓
Response:
  resultType: "complete"
  content: [...]
"""

import time
import pytest
from packages.agents.mcp.protocol import (
    McpErrorCode,
    McpInputRequest,
    McpMrtrResult,
    McpRequest,
    McpRequestMetadata,
    McpToolInputSchema,
    McpToolResult,
)
from packages.agents.mcp.server import McpServer


@pytest.fixture
def mrtr_server():
    server = McpServer(name="roe-mcp", version="1.0.0")

    def roe_handler(args):
        # If human confirmation is not supplied yet, ask for MRTR
        if "human_override_confirmed" not in args:
            return McpMrtrResult(
                roundTripToken="",  # Will be populated by server
                resultType="input_required",
                inputRequests=[
                    McpInputRequest(
                        id="human_override_confirmed",
                        type="boolean",
                        description="Confirm weapon release authorization",
                    )
                ],
                ttlMs=2000,  # 2 seconds for test
            )
        # Resumed with confirmation
        if args["human_override_confirmed"] is True:
            return McpToolResult.success({"authorization": "GRANTED", "target": args.get("target")})
        else:
            return McpToolResult.error("Authorization DENIED by operator")

    server.register_tool(
        name="authorize_kinetic_strike",
        description="Authorize kinetic strike with ROE confirmation",
        input_schema=McpToolInputSchema(
            type="object",
            properties={"target": {"type": "string"}},
            required=["target"],
        ),
        handler=roe_handler,
    )
    return server


def test_mrtr_exact_wire_shape(mrtr_server):
    """Verify full tools/call -> input_required -> inputResponses -> complete wire exchange."""
    # Step 1: Initial tools/call
    req1 = McpRequest(
        id=40,
        method="tools/call",
        params={"name": "authorize_kinetic_strike", "arguments": {"target": "BUNKER-07"}},
        metadata=McpRequestMetadata(protocol_version="2026-07-28", client_info={"name": "commander-agent"}),
    )
    resp1 = mrtr_server.handle_request(req1)

    assert resp1.error is None
    res1 = resp1.result
    assert res1["resultType"] == "input_required"
    assert "roundTripToken" in res1 and res1["roundTripToken"].startswith("mrt_")
    token = res1["roundTripToken"]
    assert "inputRequests" in res1
    assert len(res1["inputRequests"]) == 1
    assert res1["inputRequests"][0]["id"] == "human_override_confirmed"

    # Step 2: Client supplies inputResponses with roundTripToken
    req2 = McpRequest(
        id=41,
        method="tools/call",
        params={
            "name": "authorize_kinetic_strike",
            "arguments": {"target": "BUNKER-07"},
            "roundTripToken": token,
            "inputResponses": [{"id": "human_override_confirmed", "value": True}],
        },
        metadata=McpRequestMetadata(
            protocol_version="2026-07-28",
            client_info={"name": "commander-agent"},
            round_trip_token=token,
        ),
    )
    resp2 = mrtr_server.handle_request(req2)

    assert resp2.error is None
    res2 = resp2.result
    assert res2["resultType"] == "complete"
    assert res2["isError"] is False
    assert "GRANTED" in res2["content"][0]["text"]


def test_mrtr_token_replay(mrtr_server):
    """Verify that replaying an already completed roundTripToken is rejected."""
    # Initial request
    req1 = McpRequest(
        id=50,
        method="tools/call",
        params={"name": "authorize_kinetic_strike", "arguments": {"target": "BUNKER-07"}},
        metadata=McpRequestMetadata(protocol_version="2026-07-28", client_info={"name": "agent-1"}),
    )
    resp1 = mrtr_server.handle_request(req1)
    token = resp1.result["roundTripToken"]

    # First completion
    req2 = McpRequest(
        id=51,
        method="tools/call",
        params={
            "name": "authorize_kinetic_strike",
            "roundTripToken": token,
            "inputResponses": [{"id": "human_override_confirmed", "value": True}],
        },
        metadata=McpRequestMetadata(protocol_version="2026-07-28", client_info={"name": "agent-1"}),
    )
    resp2 = mrtr_server.handle_request(req2)
    assert resp2.error is None

    # Replay attack attempt with same token
    req_replay = McpRequest(
        id=52,
        method="tools/call",
        params={
            "name": "authorize_kinetic_strike",
            "roundTripToken": token,
            "inputResponses": [{"id": "human_override_confirmed", "value": True}],
        },
        metadata=McpRequestMetadata(protocol_version="2026-07-28", client_info={"name": "agent-1"}),
    )
    resp_replay = mrtr_server.handle_request(req_replay)

    assert resp_replay.error is not None
    assert "already completed" in resp_replay.error["message"]


def test_mrtr_expiration(mrtr_server):
    """Verify that an expired MRTR token cannot be resumed."""
    # Token with 1ms expiration
    token = mrtr_server.create_mrtr_session(
        client_id="agent-fast",
        tool_name="authorize_kinetic_strike",
        arguments={"target": "DEPOT"},
        input_requests=[{"id": "human_override_confirmed"}],
        ttl_ms=1,  # Expire immediately
    )
    time.sleep(0.01)

    req = McpRequest(
        id=60,
        method="tools/call",
        params={
            "name": "authorize_kinetic_strike",
            "roundTripToken": token,
            "inputResponses": [{"id": "human_override_confirmed", "value": True}],
        },
        metadata=McpRequestMetadata(protocol_version="2026-07-28", client_info={"name": "agent-fast"}),
    )
    resp = mrtr_server.handle_request(req)

    assert resp.error is not None
    assert resp.error["code"] == McpErrorCode.REQUEST_TIMEOUT
    assert "expired" in resp.error["message"]


def test_mrtr_wrong_client(mrtr_server):
    """Verify that a different client cannot claim or resume another client's MRTR token."""
    req1 = McpRequest(
        id=70,
        method="tools/call",
        params={"name": "authorize_kinetic_strike", "arguments": {"target": "RADAR-1"}},
        metadata=McpRequestMetadata(protocol_version="2026-07-28", client_info={"name": "client-A"}),
    )
    resp1 = mrtr_server.handle_request(req1)
    token = resp1.result["roundTripToken"]

    # Client-B tries to resume Client-A's token
    req_wrong = McpRequest(
        id=71,
        method="tools/call",
        params={
            "name": "authorize_kinetic_strike",
            "roundTripToken": token,
            "inputResponses": [{"id": "human_override_confirmed", "value": True}],
        },
        metadata=McpRequestMetadata(protocol_version="2026-07-28", client_info={"name": "client-B"}),
    )
    resp_wrong = mrtr_server.handle_request(req_wrong)

    assert resp_wrong.error is not None
    assert resp_wrong.error["code"] == McpErrorCode.UNAUTHORIZED
    assert "client mismatch" in resp_wrong.error["message"]


def test_mrtr_response_binding(mrtr_server):
    """Verify that responses with unexpected IDs not requested by server are rejected."""
    req1 = McpRequest(
        id=80,
        method="tools/call",
        params={"name": "authorize_kinetic_strike", "arguments": {"target": "RADAR-2"}},
        metadata=McpRequestMetadata(protocol_version="2026-07-28", client_info={"name": "agent-1"}),
    )
    resp1 = mrtr_server.handle_request(req1)
    token = resp1.result["roundTripToken"]

    req_bad_binding = McpRequest(
        id=81,
        method="tools/call",
        params={
            "name": "authorize_kinetic_strike",
            "roundTripToken": token,
            "inputResponses": [{"id": "unrelated_parameter", "value": 42}],
        },
        metadata=McpRequestMetadata(protocol_version="2026-07-28", client_info={"name": "agent-1"}),
    )
    resp_bad = mrtr_server.handle_request(req_bad_binding)

    assert resp_bad.error is not None
    assert "was not requested" in resp_bad.error["message"]


def test_mrtr_duplicate_response(mrtr_server):
    """Verify that duplicate inputResponse IDs in a single resumption are rejected."""
    req1 = McpRequest(
        id=90,
        method="tools/call",
        params={"name": "authorize_kinetic_strike", "arguments": {"target": "RADAR-3"}},
        metadata=McpRequestMetadata(protocol_version="2026-07-28", client_info={"name": "agent-1"}),
    )
    resp1 = mrtr_server.handle_request(req1)
    token = resp1.result["roundTripToken"]

    req_dupe = McpRequest(
        id=91,
        method="tools/call",
        params={
            "name": "authorize_kinetic_strike",
            "roundTripToken": token,
            "inputResponses": [
                {"id": "human_override_confirmed", "value": True},
                {"id": "human_override_confirmed", "value": False},
            ],
        },
        metadata=McpRequestMetadata(protocol_version="2026-07-28", client_info={"name": "agent-1"}),
    )
    resp_dupe = mrtr_server.handle_request(req_dupe)

    assert resp_dupe.error is not None
    assert "Duplicate inputResponse ID" in resp_dupe.error["message"]
