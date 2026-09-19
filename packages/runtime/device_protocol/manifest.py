"""ULTRONE Device Interface Standard (UDIS) - Device Manifest Specification.

Implements MHS-aligned structured machine legibility: agents discover device identities,
read/write capabilities, state schemas, procedures, constraints, and safety profiles.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

from .limits import DeviceSafetyLimits, SafetyConstraint
from .procedures import ProcedureSpec


class DeviceOperatingMode(str, Enum):
    SIMULATION = "simulation"
    DIGITAL_TWIN = "digital_twin"
    PHYSICAL = "physical"


@dataclass
class DeviceCapability:
    """Individual capability exposed by the device."""
    name: str
    description: str
    parameters_schema: Dict[str, Any] = field(default_factory=dict)
    returns_schema: Dict[str, Any] = field(default_factory=dict)
    is_read_only: bool = False
    requires_lease: bool = True


@dataclass
class DeviceSafetySpec:
    """Enforced safety boundaries for device operation."""
    simulation_only: bool = True
    e_stop_channel: str = "safety/estop"
    max_rate_hz: float = 50.0
    requires_human_approval_for_physical: bool = True
    constraints: List[SafetyConstraint] = field(default_factory=list)


@dataclass
class DeviceManifest:
    """UDIS canonical manifest making a machine legible to AI agents."""
    device_id: str
    device_type: str
    manufacturer: str = "simulated"
    model: str = "generic-udis-v1"
    firmware: str = "sim-1.0.0"
    mode: DeviceOperatingMode = DeviceOperatingMode.SIMULATION
    schema_version: str = "1.0"
    capabilities: List[DeviceCapability] = field(default_factory=list)
    state_schema: Dict[str, Any] = field(default_factory=dict)
    procedures: List[ProcedureSpec] = field(default_factory=list)
    constraints: List[SafetyConstraint] = field(default_factory=list)
    telemetry_channels: List[str] = field(default_factory=list)
    health: Dict[str, Any] = field(default_factory=dict)
    safety: DeviceSafetySpec = field(default_factory=DeviceSafetySpec)

    def get_capability(self, cap_name: str) -> Optional[DeviceCapability]:
        for cap in self.capabilities:
            if cap.name == cap_name:
                return cap
        return None

    def get_procedure(self, proc_name: str) -> Optional[ProcedureSpec]:
        for p in self.procedures:
            if p.name == proc_name or p.procedure_id == proc_name:
                return p
        return None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "device_id": self.device_id,
            "device_type": self.device_type,
            "manufacturer": self.manufacturer,
            "model": self.model,
            "firmware": self.firmware,
            "mode": self.mode.value,
            "capabilities": [
                {
                    "name": c.name,
                    "description": c.description,
                    "parameters_schema": c.parameters_schema,
                    "is_read_only": c.is_read_only,
                    "requires_lease": c.requires_lease,
                }
                for c in self.capabilities
            ],
            "state_schema": self.state_schema,
            "procedures": [p.to_dict() for p in self.procedures],
            "constraints": [
                {
                    "constraint_id": c.constraint_id,
                    "parameter": c.parameter,
                    "operator": c.operator,
                    "limit_value": c.limit_value,
                    "description": c.description,
                }
                for c in self.constraints
            ],
            "telemetry_channels": self.telemetry_channels,
            "health": self.health,
            "safety": {
                "simulation_only": self.safety.simulation_only,
                "e_stop_channel": self.safety.e_stop_channel,
                "max_rate_hz": self.safety.max_rate_hz,
            },
        }
