"""Formal Machine-Checkable Invariant Registry for ULTRONE Safety Architecture.

Declares canonical safety invariants (SAF-001 through SAF-005) with machine-checkable
verification functions, test bindings, severity levels, owners, and versions.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple


class SeverityLevel(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass(frozen=True)
class SafetyInvariant:
    """A formal safety invariant specification."""
    id: str
    name: str
    severity: SeverityLevel
    description: str
    implementation: str
    test: str
    evidence: str
    owner: str = "safety-kernel"
    version: str = "1.0.0"
    check_fn: Optional[Callable[..., Tuple[bool, Optional[str]]]] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "severity": self.severity.value,
            "description": self.description,
            "implementation": self.implementation,
            "test": self.test,
            "evidence": self.evidence,
            "owner": self.owner,
            "version": self.version,
        }


class InvariantRegistry:
    """Central registry and verification engine for formal safety invariants."""

    def __init__(self):
        self._invariants: Dict[str, SafetyInvariant] = {}
        self._load_default_invariants()

    def register(self, invariant: SafetyInvariant) -> None:
        self._invariants[invariant.id] = invariant

    def get(self, invariant_id: str) -> Optional[SafetyInvariant]:
        return self._invariants.get(invariant_id)

    def list_all(self) -> List[SafetyInvariant]:
        return list(self._invariants.values())

    def verify_invariant(self, invariant_id: str, *args, **kwargs) -> Tuple[bool, Optional[str]]:
        inv = self.get(invariant_id)
        if not inv:
            return False, f"Invariant '{invariant_id}' not found in registry"
        if not inv.check_fn:
            return False, f"Invariant '{invariant_id}' has no machine-checkable verification function"
        return inv.check_fn(*args, **kwargs)

    def _load_default_invariants(self) -> None:
        # SAF-001: no_post_action_data_in_pre_action_decision
        def check_saf_001(context: Any) -> Tuple[bool, Optional[str]]:
            from packages.runtime.event_sourcing.causal_boundary import (
                CausalBoundaryValidator,
                CausalBoundaryViolationError,
            )
            try:
                CausalBoundaryValidator.inspect_decision_inputs(context)
                return True, None
            except CausalBoundaryViolationError as e:
                return False, str(e)

        self.register(
            SafetyInvariant(
                id="SAF-001",
                name="no_post_action_data_in_pre_action_decision",
                severity=SeverityLevel.CRITICAL,
                description="Pre-action decision inputs and belief state must never contain post-action outcomes, future observations, or tainted oracle values.",
                implementation="packages.runtime.event_sourcing.causal_boundary:CausalBoundaryValidator",
                test="tests/evals/test_causal_boundary.py",
                evidence="Zero-taint and zero-forbidden-key enforcement before action gating",
                check_fn=check_saf_001,
            )
        )

        # SAF-002: expired_lease_cannot_execute
        def check_saf_002(lease: Any, now: Optional[float] = None) -> Tuple[bool, Optional[str]]:
            if lease is None:
                return False, "Lease is null"
            return lease.is_valid(now=now)

        self.register(
            SafetyInvariant(
                id="SAF-002",
                name="expired_lease_cannot_execute",
                severity=SeverityLevel.CRITICAL,
                description="No device command or procedure execution may proceed with an expired or revoked capability lease.",
                implementation="packages.runtime.device_protocol.leases:CapabilityLease",
                test="tests/udis/test_device_leases.py",
                evidence="Temporal validity check against monotonic epoch before every command dispatch",
                check_fn=check_saf_002,
            )
        )

        # SAF-003: stale_telemetry_cannot_authorize_action
        def check_saf_003(frame: Any, max_age_seconds: float = 2.0, now: Optional[float] = None) -> Tuple[bool, Optional[str]]:
            if frame is None:
                return False, "Telemetry frame is null"
            if hasattr(frame, "is_fresh"):
                if not frame.is_fresh(current_mono=now):
                    return False, f"Telemetry frame is stale (expired freshness horizon)"
                return True, None
            return False, "Object does not support freshness checks"

        self.register(
            SafetyInvariant(
                id="SAF-003",
                name="stale_telemetry_cannot_authorize_action",
                severity=SeverityLevel.HIGH,
                description="Decisions depending on device telemetry must reject any telemetry frames whose age exceeds the freshness horizon.",
                implementation="packages.runtime.device_protocol.telemetry:TelemetryBuffer",
                test="tests/udis/test_device_telemetry.py",
                evidence="Freshness gate checks frame timestamp difference against system clock",
                check_fn=check_saf_003,
            )
        )

        # SAF-004: emergency_stop_is_terminal_until_reset
        def check_saf_004(current_state: Any, target_state: Any) -> Tuple[bool, Optional[str]]:
            from packages.runtime.device_protocol.state import DeviceState
            if current_state == DeviceState.EMERGENCY_STOP:
                # Can only transition to MAINTENANCE or OFFLINE via explicit procedure
                if target_state not in (DeviceState.MAINTENANCE, DeviceState.OFFLINE):
                    return False, f"Emergency stop is terminal: cannot transition directly to '{target_state}'"
            return True, None

        self.register(
            SafetyInvariant(
                id="SAF-004",
                name="emergency_stop_is_terminal_until_reset",
                severity=SeverityLevel.CRITICAL,
                description="Once a device transitions to EMERGENCY_STOP, it cannot transition directly to an active state (EXECUTING/READY) without an explicit reset procedure.",
                implementation="packages.runtime.device_protocol.state:DeviceFSM",
                test="tests/udis/test_device_fsm.py",
                evidence="Finite state machine transition table permits only RESETTING from EMERGENCY_STOP",
                check_fn=check_saf_004,
            )
        )

        # SAF-005: physical_driver_requires_authorized_capability
        def check_saf_005(is_physical: bool, operator_token: Optional[str], capability_authorized: bool) -> Tuple[bool, Optional[str]]:
            if is_physical:
                if not operator_token or not operator_token.strip():
                    return False, "Physical actuation strictly prohibited without operator authorization token"
                if not capability_authorized:
                    return False, "Physical actuation prohibited without authorized capability lease"
            return True, None

        self.register(
            SafetyInvariant(
                id="SAF-005",
                name="physical_driver_requires_authorized_capability",
                severity=SeverityLevel.CRITICAL,
                description="Direct actuation on physical hardware drivers requires both an unrevoked capability lease and a cryptographic operator token.",
                implementation="packages.runtime.device_protocol.driver:PhysicalHardwareDriver",
                test="tests/udis/test_device_driver.py",
                evidence="Hardware driver gate validates lease and cryptographic operator signature before transmission",
                check_fn=check_saf_005,
            )
        )
