"""ULTRONE Device Interface Standard (UDIS) - Device Manifest Specification.

Implements MHS-aligned structured machine legibility: agents discover device identities,
read/write capabilities, state schemas, procedures, constraints, and safety profiles.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

try:
    from cryptography.hazmat.primitives.asymmetric import ed25519
    HAS_CRYPTOGRAPHY = True
except ImportError:
    HAS_CRYPTOGRAPHY = False

from .limits import DeviceSafetyLimits, SafetyConstraint
from .procedures import ProcedureSpec


class DeviceOperatingMode(str, Enum):
    SIMULATION = "simulation"
    DIGITAL_TWIN = "digital_twin"
    PHYSICAL = "physical"


class AuthorityLevel(str, Enum):
    """Explicit separation of observational access from physical or stateful actuation."""
    OBSERVE = "OBSERVE"
    ACTUATE = "ACTUATE"


class GranularScope(str, Enum):
    """Granular permissions governing device interaction."""
    OBSERVE_STATE = "observe.state"
    OBSERVE_TELEMETRY = "observe.telemetry"
    OBSERVE_HEALTH = "observe.health"
    SIMULATE_EXECUTE = "simulate.execute"
    SIMULATE_RESET = "simulate.reset"
    TEST_EXECUTE = "test.execute"
    PHYSICAL_REQUEST = "physical.request"
    PHYSICAL_EXECUTE = "physical.execute"
    ADMIN_CONFIGURE = "admin.configure"


@dataclass
class DeviceCapability:
    """Individual capability exposed by the device."""
    name: str
    description: str
    parameters_schema: Dict[str, Any] = field(default_factory=dict)
    returns_schema: Dict[str, Any] = field(default_factory=dict)
    is_read_only: bool = False
    requires_lease: bool = True
    authority_level: AuthorityLevel = AuthorityLevel.ACTUATE
    required_scopes: List[GranularScope] = field(default_factory=list)


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
    # Manifest Author Provenance & Cryptographic Signature
    author_identity: Optional[str] = None
    signature: Optional[str] = None
    signature_scheme: str = "ed25519"
    public_key_hex: Optional[str] = None

    def canonical_bytes(self) -> bytes:
        """Deterministic canonical bytes representation for manifest signing."""
        core = {
            "device_id": self.device_id,
            "device_type": self.device_type,
            "manufacturer": self.manufacturer,
            "model": self.model,
            "firmware": self.firmware,
            "mode": self.mode.value,
            "schema_version": self.schema_version,
            "capabilities": [c.name for c in sorted(self.capabilities, key=lambda x: x.name)],
            "author_identity": self.author_identity or "",
        }
        return json.dumps(core, sort_keys=True).encode("utf-8")

    def sign(self, private_key: Any, author_identity: str) -> None:
        """Sign manifest using author's Ed25519 private key."""
        self.author_identity = author_identity
        pub_hex = private_key.public_key().public_bytes_raw().hex()
        self.public_key_hex = pub_hex
        sig_bytes = private_key.sign(self.canonical_bytes())
        self.signature = sig_bytes.hex()
        self.signature_scheme = "ed25519"

    def verify_signature(self, public_key: Optional[Any] = None) -> Tuple[bool, Optional[str]]:
        """Verify author cryptographic signature against registry poisoning."""
        if not self.signature:
            return False, "Manifest is unsigned"
        if not HAS_CRYPTOGRAPHY:
            return False, "cryptography library required for Ed25519 verification"

        if public_key is None:
            if not self.public_key_hex:
                return False, "No public key available for verification"
            try:
                pub = ed25519.Ed25519PublicKey.from_public_bytes(bytes.fromhex(self.public_key_hex))
            except Exception as e:
                return False, f"Invalid public key hex: {e}"
        else:
            pub = public_key

        try:
            pub.verify(bytes.fromhex(self.signature), self.canonical_bytes())
            return True, None
        except Exception:
            return False, "Cryptographic signature mismatch: Manifest has been tampered with"

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
