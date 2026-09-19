"""Tests for UDIS Deterministic Procedures and compilation."""

import pytest
from packages.runtime.device_protocol.driver import SimulationDeviceDriver
from packages.runtime.device_protocol.manifest import (
    DeviceCapability,
    DeviceManifest,
    DeviceOperatingMode,
    DeviceSafetySpec,
)
from packages.runtime.device_protocol.procedures import ProcedureCompiler, ProcedureRunner


def _create_mock_driver():
    manifest = DeviceManifest(
        device_id="gimbal-01",
        device_type="eo_ir_turret",
        mode=DeviceOperatingMode.SIMULATION,
        capabilities=[
            DeviceCapability(name="pan", description="Pan angle"),
            DeviceCapability(name="tilt", description="Tilt angle"),
            DeviceCapability(name="capture", description="Capture frame"),
        ],
        safety=DeviceSafetySpec(simulation_only=True),
    )
    driver = SimulationDeviceDriver(manifest)
    driver.connect()
    return driver


def test_procedure_compilation_and_execution():
    driver = _create_mock_driver()

    # Discovered sequence of actions
    explored_actions = [
        {"command": "pan", "params": {"angle_deg": 45.0}},
        {"command": "tilt", "params": {"angle_deg": -15.0}},
        {"command": "capture", "params": {"resolution": "4K"}},
    ]

    procedure = ProcedureCompiler.compile_from_actions(
        name="scan_northeast_quadrant",
        description="Pans 45 deg, tilts down 15 deg, and captures 4K snapshot",
        actions=explored_actions,
    )

    assert procedure.name == "scan_northeast_quadrant"
    assert len(procedure.steps) == 3
    assert set(procedure.required_capabilities) == {"pan", "tilt", "capture"}

    # Execute deterministically
    runner = ProcedureRunner(driver)
    res = runner.execute(procedure)

    assert res.success is True
    assert res.steps_completed == 3
    assert res.total_steps == 3
    assert res.error is None
    assert len(res.step_results) == 3


def test_procedure_parameter_interpolation():
    driver = _create_mock_driver()

    explored_actions = [
        {"command": "pan", "params": {"angle_deg": "$target_azimuth"}},
        {"command": "capture", "params": {"zoom": "$zoom_factor"}},
    ]

    procedure = ProcedureCompiler.compile_from_actions(
        name="dynamic_tracking_snapshot",
        description="Interpolates target params dynamically",
        actions=explored_actions,
    )

    runner = ProcedureRunner(driver)
    res = runner.execute(procedure, execution_params={"target_azimuth": 90.0, "zoom_factor": "10x"})

    assert res.success is True
    assert res.step_results[0]["result"]["executed_params"]["angle_deg"] == 90.0
    assert res.step_results[1]["result"]["executed_params"]["zoom"] == "10x"
