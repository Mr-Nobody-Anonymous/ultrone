# Copyright (c) Ultrone Contributors. All rights reserved.
import json
import pytest

from packages.agents.mcp import (
    ActuatorMcpServer,
    McpClient,
    McpServer,
    McpToolBridge,
    SensorMcpServer,
)
from packages.agents.tools import ToolRuntime


def test_mcp_server_client_handshake_and_ping():
    server = McpServer(name="test-server", version="0.1.0")
    client = McpClient(server=server)

    init_res = client.connect()
    assert init_res["protocolVersion"] == "2024-11-05"
    assert init_res["serverInfo"]["name"] == "test-server"

    ping_res = client.send_request("ping", {})
    assert ping_res.result == {}
    assert ping_res.error is None


def test_mcp_custom_tool_registration_and_execution():
    server = McpServer(name="calc-server")
    server.register_tool(
        name="multiply",
        description="Multiplies two numbers",
        input_schema={
            "type": "object",
            "properties": {
                "x": {"type": "number"},
                "y": {"type": "number"},
            },
            "required": ["x", "y"],
        },
        handler=lambda args: {"product": args["x"] * args["y"]},
    )

    client = McpClient(server=server)
    client.connect()

    tools = client.list_tools()
    assert len(tools) == 1
    assert tools[0].name == "multiply"

    # Execution success
    call_res = client.call_tool("multiply", {"x": 7, "y": 6})
    assert not call_res.isError
    assert len(call_res.content) == 1
    data = json.loads(call_res.content[0].text)
    assert data["product"] == 42

    # Execution failure: missing required parameter
    fail_res = client.call_tool("multiply", {"x": 5})
    assert fail_res.isError
    assert "Missing required parameter" in fail_res.content[0].text


def test_sensor_mcp_server_tools_and_resources():
    sensor_server = SensorMcpServer()
    client = McpClient(server=sensor_server)
    client.connect()

    tools = client.list_tools()
    tool_names = {t.name for t in tools}
    assert "radar_sweep" in tool_names
    assert "satellite_sar_capture" in tool_names
    assert "query_telemetry" in tool_names
    assert "eoir_track_target" in tool_names

    # Test radar sweep
    res_radar = client.call_tool("radar_sweep", {"sector_center_deg": 45.0, "max_range_km": 80.0})
    assert not res_radar.isError
    radar_data = json.loads(res_radar.content[0].text)
    assert radar_data["sweep_complete"] is True
    assert len(radar_data["tracks"]) >= 1

    # Test SAR capture
    res_sar = client.call_tool("satellite_sar_capture", {"target_lat": 34.05, "target_lon": -118.24})
    assert not res_sar.isError
    sar_data = json.loads(res_sar.content[0].text)
    assert "capture_id" in sar_data

    # Test reading resource
    resources = client.list_resources()
    assert any("radar/active_tracks" in r.uri for r in resources)
    tracks_json = client.read_resource("sensor://radar/active_tracks")
    tracks_list = json.loads(tracks_json)
    assert isinstance(tracks_list, list)
    assert len(tracks_list) >= 1


def test_actuator_mcp_server_clearance_token_enforcement():
    actuator_server = ActuatorMcpServer()
    client = McpClient(server=actuator_server)
    client.connect()

    # Dispatch waypoint
    wp_res = client.call_tool(
        "dispatch_waypoint",
        {"unit_id": "UAV-ALFA-1", "lat": 34.10, "lon": -118.30, "alt_m": 3000.0},
    )
    assert not wp_res.isError
    assert json.loads(wp_res.content[0].text)["status"] == "WAYPOINT_ACCEPTED"

    # Unauthorized strike rejected without valid token
    strike_unauth = client.call_tool(
        "designate_target",
        {
            "unit_id": "UAV-ALFA-1",
            "target_id": "TRK-001",
            "weapon_mode": "kinetic",
            "roe_clearance_token": "UNAUTHORIZED_ATTEMPT",
        },
    )
    assert strike_unauth.isError
    assert "Invalid ROE clearance token" in strike_unauth.content[0].text

    # Authorized strike succeeds with proper token
    strike_auth = client.call_tool(
        "designate_target",
        {
            "unit_id": "UAV-ALFA-1",
            "target_id": "TRK-001",
            "weapon_mode": "laser_guided",
            "roe_clearance_token": "ROE-CLEARED-9988AABBCCDDEEFF",
        },
    )
    assert not strike_auth.isError
    auth_data = json.loads(strike_auth.content[0].text)
    assert auth_data["status"] == "TARGET_ENGAGED"


def test_mcp_tool_bridge_into_tool_runtime():
    sensor_server = SensorMcpServer()
    client = McpClient(server=sensor_server)
    client.connect()

    bridge = McpToolBridge(client=client)
    registered = bridge.sync_tools()
    assert "radar_sweep" in registered

    runtime = ToolRuntime(registry=bridge.registry)
    run_res = runtime.execute("radar_sweep", {"sector_center_deg": 180.0}, caller_agent_id="test-harness")
    assert run_res.success
    assert run_res.output["sweep_complete"] is True
    assert len(runtime.audit_logger.get_entries()) == 1
