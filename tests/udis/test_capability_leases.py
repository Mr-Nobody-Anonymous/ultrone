"""Tests for UDIS Capability Leases, scoped authority, and rate-limiting."""

import time
import pytest
from packages.runtime.device_protocol.leases import LeaseManager


def test_lease_grant_and_scope_validation():
    manager = LeaseManager()
    lease = manager.request_lease(
        agent_id="strike-worker-01",
        device_id="sensor-pod-01",
        capabilities={"read_radar", "scan_sector"},
        duration_seconds=10.0,
        purpose="isr_reconnaissance",
        is_simulation=True,
    )

    assert lease.lease_id.startswith("lease-")
    assert lease.has_capability("read_radar")
    assert lease.has_capability("scan_sector")
    assert not lease.has_capability("fire_weapon")

    # Validate action through manager
    ok, err = manager.validate_action(lease.lease_id, "read_radar")
    assert ok is True
    assert err is None

    # Unauthorized action rejected
    ok, err = manager.validate_action(lease.lease_id, "fire_weapon")
    assert ok is False
    assert "does not grant capability 'fire_weapon'" in err


def test_lease_expiration():
    manager = LeaseManager()
    lease = manager.request_lease(
        agent_id="test-agent",
        device_id="sensor-01",
        capabilities={"read_radar"},
        duration_seconds=0.05,  # 50ms TTL
    )

    # Immediately valid
    ok, _ = manager.validate_action(lease.lease_id, "read_radar")
    assert ok is True

    # Sleep past expiration
    time.sleep(0.08)
    ok, err = manager.validate_action(lease.lease_id, "read_radar")
    assert ok is False
    assert "expired" in err


def test_lease_rate_limiting():
    manager = LeaseManager()
    lease = manager.request_lease(
        agent_id="agent-fast",
        device_id="device-01",
        capabilities={"ping"},
        duration_seconds=60.0,
        rate_limit_per_min=3,  # Max 3 calls per minute
    )

    # 3 calls succeed
    assert manager.validate_action(lease.lease_id, "ping")[0] is True
    assert manager.validate_action(lease.lease_id, "ping")[0] is True
    assert manager.validate_action(lease.lease_id, "ping")[0] is True

    # 4th call within minute fails with rate limit error
    ok, err = manager.validate_action(lease.lease_id, "ping")
    assert ok is False
    assert "Rate limit of 3 calls/min exceeded" in err


def test_lease_revocation():
    manager = LeaseManager()
    lease = manager.request_lease(
        agent_id="agent-01",
        device_id="device-01",
        capabilities={"move"},
    )

    ok, _ = manager.validate_action(lease.lease_id, "move")
    assert ok is True

    # Operator revokes lease
    manager.revoke_lease(lease.lease_id, reason="Mission aborted")
    ok, err = manager.validate_action(lease.lease_id, "move")
    assert ok is False
    assert "revoked" in err
