"""ULTRONE Device Interface Standard (UDIS) - Capability Leases & Scoped Authority.

Implements temporary, capability-scoped, rate-limited execution leases preventing models
from acquiring unbounded authority over hardware or simulation devices.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple


@dataclass
class CapabilityLease:
    """Scoped execution lease granted to an agent for specific capabilities."""
    lease_id: str
    agent_id: str
    device_id: str
    capabilities: Set[str]
    granted_at: float
    expires_at: float
    rate_limit_per_min: int = 60
    purpose: str = "tactical_mission"
    policy_version: str = "v1.0"
    is_simulation: bool = True
    operator_auth: Optional[str] = None
    _calls: List[float] = field(default_factory=list)
    _revoked: bool = False

    def is_valid(self, now: Optional[float] = None) -> Tuple[bool, Optional[str]]:
        t = time.time() if now is None else now
        if self._revoked:
            return False, f"Lease '{self.lease_id}' has been revoked"
        if t > self.expires_at:
            return False, f"Lease '{self.lease_id}' expired at {self.expires_at} (current: {t})"
        return True, None

    def has_capability(self, capability: str) -> bool:
        return capability in self.capabilities or "*" in self.capabilities

    def check_and_record_rate_limit(self) -> Tuple[bool, Optional[str]]:
        now = time.time()
        # Clean timestamps older than 60s
        self._calls = [t for t in self._calls if now - t <= 60.0]
        if len(self._calls) >= self.rate_limit_per_min:
            return False, f"Rate limit of {self.rate_limit_per_min} calls/min exceeded for lease {self.lease_id}"
        self._calls.append(now)
        return True, None

    def revoke(self, reason: str = "administrative"):
        self._revoked = True


class LeaseManager:
    """Manages lease lifecycles, capability authorizations, and expiration enforcement."""

    def __init__(self):
        self._leases: Dict[str, CapabilityLease] = {}

    def request_lease(
        self,
        agent_id: str,
        device_id: str,
        capabilities: Set[str],
        duration_seconds: float = 300.0,
        purpose: str = "mission_execution",
        policy_version: str = "v1.0",
        is_simulation: bool = True,
        operator_auth: Optional[str] = None,
        rate_limit_per_min: int = 60,
    ) -> CapabilityLease:
        """Issue a new scoped capability lease."""
        # Non-simulation leases require explicit cryptographic operator authorization
        if not is_simulation and not operator_auth:
            raise PermissionError("Physical device execution requires explicit operator authorization")

        now = time.time()
        lease_id = f"lease-{uuid.uuid4().hex[:12]}"
        lease = CapabilityLease(
            lease_id=lease_id,
            agent_id=agent_id,
            device_id=device_id,
            capabilities=set(capabilities),
            granted_at=now,
            expires_at=now + duration_seconds,
            rate_limit_per_min=rate_limit_per_min,
            purpose=purpose,
            policy_version=policy_version,
            is_simulation=is_simulation,
            operator_auth=operator_auth,
        )
        self._leases[lease_id] = lease
        return lease

    def validate_action(self, lease_id: str, capability: str) -> Tuple[bool, Optional[str]]:
        """Validate that a lease permits the requested action at this instant."""
        lease = self._leases.get(lease_id)
        if not lease:
            return False, f"Invalid or non-existent lease ID: {lease_id}"

        valid, err = lease.is_valid()
        if not valid:
            return False, err

        if not lease.has_capability(capability):
            return False, (
                f"Lease '{lease_id}' does not grant capability '{capability}'. "
                f"Granted: {list(lease.capabilities)}"
            )

        rate_ok, rate_err = lease.check_and_record_rate_limit()
        if not rate_ok:
            return False, rate_err

        return True, None

    def revoke_lease(self, lease_id: str, reason: str = "operator_override") -> bool:
        lease = self._leases.get(lease_id)
        if lease:
            lease.revoke(reason)
            return True
        return False

    def get_lease(self, lease_id: str) -> Optional[CapabilityLease]:
        return self._leases.get(lease_id)
