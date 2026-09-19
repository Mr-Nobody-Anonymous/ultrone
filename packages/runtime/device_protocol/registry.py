"""ULTRONE Device Interface Standard (UDIS) - Device Registry.

Central discovery, capability indexing, and lease-authorized access point for all
UDIS hardware, digital twins, and simulated apparatuses.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from .driver import BaseDeviceDriver
from .leases import LeaseManager
from .manifest import DeviceManifest
from .procedures import ProcedureExecutionResult, ProcedureRunner

logger = logging.getLogger("udis.registry")


class DeviceRegistry:
    """Registry coordinating discovery, capabilities, states, procedures, and leases."""

    def __init__(self, lease_manager: Optional[LeaseManager] = None):
        self._devices: Dict[str, BaseDeviceDriver] = {}
        self.lease_manager = lease_manager or LeaseManager()

    def register_device(self, manifest: DeviceManifest, driver: BaseDeviceDriver):
        """Register a device and connect its driver."""
        self._devices[manifest.device_id] = driver
        if not driver._connected:
            driver.connect()
        logger.info(f"Registered UDIS device: {manifest.device_id} ({manifest.device_type})")

    def unregister_device(self, device_id: str):
        if device_id in self._devices:
            self._devices[device_id].disconnect()
            del self._devices[device_id]

    def devices_list(self) -> List[Dict[str, Any]]:
        """MHS capability: devices/list."""
        return [
            {
                "device_id": d.manifest.device_id,
                "device_type": d.manifest.device_type,
                "model": d.manifest.model,
                "mode": d.manifest.mode.value,
                "state": d.get_state().value,
                "simulation_only": d.manifest.safety.simulation_only,
            }
            for d in self._devices.values()
        ]

    def devices_get(self, device_id: str) -> Optional[Dict[str, Any]]:
        """MHS capability: devices/get."""
        driver = self._devices.get(device_id)
        if not driver:
            return None
        info = driver.manifest.to_dict()
        info["current_state"] = driver.get_state().value
        return info

    def devices_capabilities(self, device_id: str) -> List[Dict[str, Any]]:
        """MHS capability: devices/capabilities."""
        driver = self._devices.get(device_id)
        if not driver:
            raise KeyError(f"Device '{device_id}' not found")
        return [
            {
                "name": c.name,
                "description": c.description,
                "parameters_schema": c.parameters_schema,
                "is_read_only": c.is_read_only,
                "requires_lease": c.requires_lease,
            }
            for c in driver.manifest.capabilities
        ]

    def devices_state(self, device_id: str) -> Dict[str, Any]:
        """MHS capability: devices/state."""
        driver = self._devices.get(device_id)
        if not driver:
            raise KeyError(f"Device '{device_id}' not found")
        return {
            "device_id": device_id,
            "state": driver.get_state().value,
            "is_operational": driver.state_machine.is_operational(),
            "telemetry": {
                ch: m.to_dict()
                for ch, m in driver.telemetry.get_all_fresh().items()
            },
        }

    def devices_health(self, device_id: str) -> Dict[str, Any]:
        """MHS capability: devices/health."""
        driver = self._devices.get(device_id)
        if not driver:
            raise KeyError(f"Device '{device_id}' not found")
        return {
            "device_id": device_id,
            "status": "healthy" if driver.get_state().value in ("READY", "SIMULATION") else "degraded",
            "state": driver.get_state().value,
            "health_metadata": driver.manifest.health,
        }

    def devices_procedures(self, device_id: str) -> List[Dict[str, Any]]:
        """MHS capability: devices/procedures."""
        driver = self._devices.get(device_id)
        if not driver:
            raise KeyError(f"Device '{device_id}' not found")
        return [p.to_dict() for p in driver.manifest.procedures]

    def execute_command(
        self,
        device_id: str,
        command: str,
        params: Dict[str, Any],
        lease_id: Optional[str] = None,
    ) -> Any:
        """Execute command against device, validating capability lease if required."""
        driver = self._devices.get(device_id)
        if not driver:
            raise KeyError(f"Device '{device_id}' not registered")

        cap = driver.manifest.get_capability(command)
        if cap and cap.requires_lease:
            if not lease_id:
                raise PermissionError(f"Command '{command}' on device '{device_id}' requires a capability lease")
            valid, err = self.lease_manager.validate_action(lease_id, command)
            if not valid:
                raise PermissionError(f"Lease authorization failed: {err}")

        return driver.execute_command(command, params)

    def execute_procedure(
        self,
        device_id: str,
        procedure_name: str,
        params: Optional[Dict[str, Any]] = None,
        lease_id: Optional[str] = None,
    ) -> ProcedureExecutionResult:
        """Execute a compiled deterministic procedure against a device driver."""
        driver = self._devices.get(device_id)
        if not driver:
            raise KeyError(f"Device '{device_id}' not registered")

        proc = driver.manifest.get_procedure(procedure_name)
        if not proc:
            raise KeyError(f"Procedure '{procedure_name}' not found on device '{device_id}'")

        # Check capability lease for all required capabilities in procedure
        if lease_id:
            for cap_name in proc.required_capabilities:
                valid, err = self.lease_manager.validate_action(lease_id, cap_name)
                if not valid:
                    raise PermissionError(f"Lease does not authorize procedure requirement '{cap_name}': {err}")

        runner = ProcedureRunner(driver)
        return runner.execute(proc, params)
