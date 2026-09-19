"""Tests for UDIS Device Manifest, 10-State FSM, and Safety Constraints."""

import pytest
from packages.runtime.device_protocol.limits import DeviceSafetyLimits, SafetyConstraint
from packages.runtime.device_protocol.manifest import (
    DeviceCapability,
    DeviceManifest,
    DeviceOperatingMode,
    DeviceSafetySpec,
)
from packages.runtime.device_protocol.state import (
    DeviceState,
    DeviceStateMachine,
    InvalidStateTransitionError,
)


def test_device_manifest_creation_and_serialization():
    manifest = DeviceManifest(
        device_id="uav-alpha-01",
        device_type="recon_drone",
        mode=DeviceOperatingMode.SIMULATION,
        capabilities=[
            DeviceCapability(
                name="set_waypoint",
                description="Navigate to 3D waypoint",
                parameters_schema={"x": "float", "y": "float", "z": "float"},
                is_read_only=False,
                requires_lease=True,
            ),
            DeviceCapability(
                name="read_battery",
                description="Telemetry read",
                is_read_only=True,
                requires_lease=False,
            ),
        ],
        safety=DeviceSafetySpec(simulation_only=True),
    )

    d = manifest.to_dict()
    assert d["device_id"] == "uav-alpha-01"
    assert d["mode"] == "simulation"
    assert d["safety"]["simulation_only"] is True
    assert len(d["capabilities"]) == 2


def test_device_state_machine_valid_lifecycle():
    fsm = DeviceStateMachine(device_id="uav-01", initial_state=DeviceState.DISCOVERING)
    assert fsm.current_state == DeviceState.DISCOVERING
    assert not fsm.is_operational()

    # Discovering -> Simulation
    t1 = fsm.transition_to(DeviceState.SIMULATION, reason="Virtual initialization")
    assert fsm.current_state == DeviceState.SIMULATION
    assert fsm.is_operational()
    assert t1.to_state == DeviceState.SIMULATION

    # Simulation -> Busy -> Simulation
    fsm.transition_to(DeviceState.BUSY, reason="Executing waypoint navigation")
    assert fsm.current_state == DeviceState.BUSY
    fsm.transition_to(DeviceState.SIMULATION, reason="Waypoint reached")
    assert fsm.current_state == DeviceState.SIMULATION


def test_device_state_machine_invalid_transition_raises():
    fsm = DeviceStateMachine(device_id="uav-01", initial_state=DeviceState.DISCOVERING)

    # DISCOVERING cannot transition directly to BUSY
    with pytest.raises(InvalidStateTransitionError):
        fsm.transition_to(DeviceState.BUSY, reason="Illegal direct busy transition")


def test_device_emergency_stop():
    fsm = DeviceStateMachine(device_id="uav-01", initial_state=DeviceState.READY)
    fsm.emergency_stop(reason="Obstacle collision imminent")
    assert fsm.current_state == DeviceState.EMERGENCY_STOP
    assert not fsm.is_operational()

    # Once in EMERGENCY_STOP, cannot transition directly to READY
    with pytest.raises(InvalidStateTransitionError):
        fsm.transition_to(DeviceState.READY, reason="Direct resume forbidden")

    # Must transition to MAINTENANCE first
    fsm.transition_to(DeviceState.MAINTENANCE, reason="Safety diagnostics")
    assert fsm.current_state == DeviceState.MAINTENANCE


def test_safety_constraints_validation():
    constraints = [
        SafetyConstraint(
            constraint_id="c_speed",
            parameter="speed_mps",
            operator="<=",
            limit_value=35.0,
            description="Max flight speed",
        ),
        SafetyConstraint(
            constraint_id="c_alt",
            parameter="altitude_m",
            operator="range",
            limit_value=(10.0, 150.0),
            description="Operational altitude envelope",
        ),
    ]
    limits = DeviceSafetyLimits(device_id="uav-01", constraints=constraints)

    # Valid parameters
    ok, violations = limits.verify_parameters({"speed_mps": 25.0, "altitude_m": 80.0})
    assert ok is True
    assert len(violations) == 0

    # Speed violation
    ok, violations = limits.verify_parameters({"speed_mps": 42.0, "altitude_m": 80.0})
    assert ok is False
    assert any("c_speed" in v for v in violations)

    # Altitude violation
    ok, violations = limits.verify_parameters({"speed_mps": 20.0, "altitude_m": 5.0})
    assert ok is False
    assert any("c_alt" in v for v in violations)
