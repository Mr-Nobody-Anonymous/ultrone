"""Tests for UDIS MCP Gateway bridging MHS-style devices into MCP 2026-07-28."""

import pytest
from packages.agents.mcp.protocol import McpRequest
from packages.agents.mcp.udis_gateway import UdisMcpGateway
from packages.runtime.device_protocol.driver import SimulationDeviceDriver
from packages.runtime.device_protocol.manifest import (
    DeviceCapability,
    DeviceManifest,
    DeviceOperatingMode,
    DeviceSafetySpec,
)
from packages.runtime.device_protocol.procedures import ProcedureCompiler
from packages.runtime.device_protocol.registry import DeviceRegistry


@pytest.fixture
def udis_gateway():
    registry = DeviceRegistry()
    proc = ProcedureCompiler.compile_from_actions(
        name="calibrate_sensor",
        description="Run calibration sequence",
        actions=[{"command": "ping", "params": {}}],
    )
    manifest = DeviceManifest(
        device_id="radar-array-01",
        device_type="active_electronically_scanned_array",
        mode=DeviceOperatingMode.SIMULATION,
        capabilities=[
            DeviceCapability(name="ping", description="Ping array"),
            DeviceCapability(name="sweep", description="Radar sweep", requires_lease=True),
        ],
        procedures=[proc],
        safety=DeviceSafetySpec(simulation_only=True),
    )
    driver = SimulationDeviceDriver(manifest)
    registry.register_device(manifest, driver)
    return UdisMcpGateway(registry)


import json


def _payload(res):
    assert res.error is None
    assert not res.result.get("isError", False)
    content = res.result["content"]
    assert len(content) > 0
    return json.loads(content[0]["text"])


def test_mcp_devices_list_tool(udis_gateway):
    req = McpRequest(
        method="tools/call",
        params={"name": "devices_list", "arguments": {}},
        id=1,
    )
    res = udis_gateway.handle_request(req)
    data = _payload(res)
    assert "devices" in data
    devices = data["devices"]
    assert len(devices) == 1
    assert devices[0]["device_id"] == "radar-array-01"
    assert devices[0]["simulation_only"] is True


def test_mcp_devices_get_and_state_tool(udis_gateway):
    # devices_get
    req_get = McpRequest(
        method="tools/call",
        params={"name": "devices_get", "arguments": {"device_id": "radar-array-01"}},
        id=2,
    )
    res_get = udis_gateway.handle_request(req_get)
    data_get = _payload(res_get)
    assert data_get["device_id"] == "radar-array-01"

    # devices_state
    req_state = McpRequest(
        method="tools/call",
        params={"name": "devices_state", "arguments": {"device_id": "radar-array-01"}},
        id=3,
    )
    res_state = udis_gateway.handle_request(req_state)
    data_state = _payload(res_state)
    assert data_state["state"] in ("SIMULATION", "READY")
    assert data_state["is_operational"] is True


def test_mcp_lease_request_and_command_execution(udis_gateway):
    # 1. Request capability lease for sweep
    req_lease = McpRequest(
        method="tools/call",
        params={
            "name": "request_lease",
            "arguments": {
                "agent_id": "recon-worker",
                "device_id": "radar-array-01",
                "capabilities": ["sweep"],
                "duration_seconds": 60.0,
            },
        },
        id=4,
    )
    res_lease = udis_gateway.handle_request(req_lease)
    data_lease = _payload(res_lease)
    lease_id = data_lease["lease_id"]
    assert lease_id.startswith("lease-")

    # 2. Execute command with lease
    req_cmd = McpRequest(
        method="tools/call",
        params={
            "name": "execute_command",
            "arguments": {
                "device_id": "radar-array-01",
                "command": "sweep",
                "params": {"azimuth_start": 0, "azimuth_end": 180},
                "lease_id": lease_id,
            },
        },
        id=5,
    )
    res_cmd = udis_gateway.handle_request(req_cmd)
    data_cmd = _payload(res_cmd)
    assert data_cmd["status"] == "success"


def test_mcp_execute_procedure(udis_gateway):
    req_proc = McpRequest(
        method="tools/call",
        params={
            "name": "execute_procedure",
            "arguments": {
                "device_id": "radar-array-01",
                "procedure_name": "calibrate_sensor",
            },
        },
        id=6,
    )
    res_proc = udis_gateway.handle_request(req_proc)
    data_proc = _payload(res_proc)
    assert data_proc["success"] is True
    assert data_proc["steps_completed"] == 1
