"""ULTRONE Device Interface Standard (UDIS) - Device Drivers.

Implements base driver abstractions, simulation drivers, and digital twin bridges.
Strictly prohibits direct physical hardware actuation without cryptographically signed authorization.
"""

from __future__ import annotations

import abc
import time
from typing import Any, Dict, Optional

from .limits import DeviceSafetyLimits
from .manifest import DeviceManifest, DeviceOperatingMode
from .state import DeviceState, DeviceStateMachine, InvalidStateTransitionError
from .telemetry import DeviceTelemetryMeasurement, TelemetryStreamBuffer


class BaseDeviceDriver(abc.ABC):
    """Abstract base driver for all UDIS compatible devices."""

    def __init__(self, manifest: DeviceManifest):
        self.manifest = manifest
        self.state_machine = DeviceStateMachine(
            device_id=manifest.device_id,
            initial_state=DeviceState.DISCOVERING,
        )
        self.telemetry = TelemetryStreamBuffer(device_id=manifest.device_id)
        self.safety_limits = DeviceSafetyLimits(
            device_id=manifest.device_id,
            simulation_only=manifest.safety.simulation_only,
            constraints=manifest.constraints,
        )
        self._connected: bool = False

    @property
    def device_id(self) -> str:
        return self.manifest.device_id

    def connect(self) -> bool:
        """Initialize connection and transition state machine."""
        target = DeviceState.SIMULATION if self.manifest.mode == DeviceOperatingMode.SIMULATION else DeviceState.READY
        self.state_machine.transition_to(target, reason="Driver connected successfully")
        self._connected = True
        return True

    def disconnect(self) -> bool:
        """Safely disconnect device."""
        self.state_machine.transition_to(DeviceState.OFFLINE, reason="Driver disconnected")
        self._connected = False
        return True

    def get_state(self) -> DeviceState:
        return self.state_machine.current_state

    def emergency_stop(self, reason: str = "Operator commanded E-STOP"):
        """Instantaneous emergency stop halting all device actions."""
        self.state_machine.emergency_stop(reason=reason)

    def execute_command(self, command: str, params: Dict[str, Any]) -> Any:
        """Execute a low-level command with guard validation and safety enforcement."""
        if not self._connected:
            raise RuntimeError(f"Device '{self.device_id}' is not connected")

        if not self.state_machine.is_operational():
            raise RuntimeError(
                f"Device '{self.device_id}' cannot execute commands while in state {self.state_machine.current_state.value}"
            )

        # Enforce safety constraints
        ok, violations = self.safety_limits.verify_parameters(params)
        if not ok:
            raise ValueError(f"Safety constraint violation on '{self.device_id}': {'; '.join(violations)}")

        # Transition to BUSY during execution, then return
        prev_state = self.state_machine.current_state
        self.state_machine.transition_to(DeviceState.BUSY, reason=f"Executing command: {command}")
        try:
            result = self._dispatch_command(command, params)
            return result
        finally:
            if self.state_machine.current_state == DeviceState.BUSY:
                self.state_machine.transition_to(prev_state, reason=f"Completed command: {command}")

    @abc.abstractmethod
    def _dispatch_command(self, command: str, params: Dict[str, Any]) -> Any:
        """Subclass implementation of device-specific command execution."""
        pass


class SimulationDeviceDriver(BaseDeviceDriver):
    """General-purpose in-memory simulation driver for autonomy and agent evaluations."""

    def __init__(self, manifest: DeviceManifest):
        super().__init__(manifest)
        self._mock_registers: Dict[str, Any] = {}

    def _dispatch_command(self, command: str, params: Dict[str, Any]) -> Dict[str, Any]:
        self._mock_registers[command] = params
        # Stream telemetry update
        self.telemetry.push(
            channel=f"commands/{command}",
            value=params,
            quality=1.0,
            confidence=1.0,
            source="sim_driver",
        )
        return {"status": "success", "command": command, "executed_params": params}


class DigitalTwinDeviceDriver(BaseDeviceDriver):
    """Digital twin driver mirroring simulation dynamics."""

    def __init__(self, manifest: DeviceManifest, fidelity: str = "high"):
        super().__init__(manifest)
        self.fidelity = fidelity
        self._state_mirror: Dict[str, Any] = {}

    def _dispatch_command(self, command: str, params: Dict[str, Any]) -> Dict[str, Any]:
        self._state_mirror[command] = params
        self.telemetry.push(
            channel=f"twin/{command}",
            value=params,
            quality=1.0,
            confidence=0.98,
            source="digital_twin",
        )
        return {"status": "mirrored", "command": command, "fidelity": self.fidelity, "params": params}


class PhysicalDeviceDriver(BaseDeviceDriver):
    """Physical hardware driver stub with strict cryptographic boundary enforcement."""

    def __init__(self, manifest: DeviceManifest, physical_token: Optional[str] = None):
        if manifest.safety.simulation_only:
            raise PermissionError(
                f"Device '{manifest.device_id}' is flagged simulation_only=True. "
                "Physical actuation is prohibited by safety policy."
            )
        if not physical_token:
            raise PermissionError("Physical device driver requires cryptographic operator authorization token.")
        super().__init__(manifest)
        self.physical_token = physical_token

    def _dispatch_command(self, command: str, params: Dict[str, Any]) -> Any:
        raise NotImplementedError("Physical device actuation disabled in this research preview.")
