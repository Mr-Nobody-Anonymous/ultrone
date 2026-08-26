# Copyright (c) Ultrone Contributors. All rights reserved.
"""Simulated computing-node subsystems (cyber platforms).

Model the internal control surfaces of a simulated machine -- compute,
storage, network interface, hosted services, authentication, monitoring,
configuration, and DEFENSIVE controls -- as ordinary command-handling
subsystems.

Simulation boundary: these model defensive operations of a sandboxed
simulated node only. There is deliberately no offensive-tooling surface
and no path toward operating real computer systems or networks here;
offensive-adjacent research belongs to dedicated sandbox environments,
not to this command interface.
"""

from __future__ import annotations

import hashlib
from collections import deque
from typing import Any, Dict, Optional

from agents.subsystems.base import Subsystem, command


class ComputeSubsystem(Subsystem):
    """CPU-like capacity with allocation tracking."""

    name = "compute"

    def __init__(self, cores: int = 4) -> None:
        super().__init__()
        self.cores = int(cores)
        self.allocated_pct = 0.0

    @command("allocate")
    def allocate(self, pct: float = 10.0) -> float:
        requested = self.allocated_pct + float(pct)
        if requested > 100.0:
            raise RuntimeError("compute allocation exceeds 100%")
        self.allocated_pct = requested
        return round(self.allocated_pct, 3)

    @command("release")
    def release(self, pct: float = 10.0) -> float:
        self.allocated_pct = max(0.0, self.allocated_pct - float(pct))
        return round(self.allocated_pct, 3)

    def status(self) -> Dict[str, Any]:
        return {**super().status(), "cores": self.cores,
                "allocated_pct": round(self.allocated_pct, 3)}


class StorageSubsystem(Subsystem):
    """Named-capacity storage pool with write/read/purge."""

    name = "storage"

    def __init__(self, capacity_gb: float = 64.0) -> None:
        super().__init__()
        self.capacity_gb = float(capacity_gb)
        self.used_gb = 0.0

    @command("write")
    def write(self, gb: float = 0.0) -> float:
        gb = float(gb)
        if gb < 0 or self.used_gb + gb > self.capacity_gb:
            raise RuntimeError("storage write exceeds capacity")
        self.used_gb += gb
        return round(self.used_gb, 3)

    @command("read")
    def read(self) -> float:
        return round(self.used_gb, 3)

    @command("purge")
    def purge(self) -> float:
        self.used_gb = 0.0
        return 0.0

    def status(self) -> Dict[str, Any]:
        return {**super().status(),
                "used_gb": round(self.used_gb, 3),
                "capacity_gb": round(self.capacity_gb, 3)}


class NetworkInterfaceSubsystem(Subsystem):
    """Link state and bandwidth reservation for a simulated node."""

    name = "network"

    def __init__(self, bandwidth_mbps: float = 100.0) -> None:
        super().__init__()
        self.bandwidth_cap_mbps = float(bandwidth_mbps)
        self.reserved_mbps = 0.0
        self.connected = False

    @command("connect")
    def connect(self, reserve_mbps: float = 10.0) -> bool:
        if float(reserve_mbps) > self.bandwidth_cap_mbps:
            raise RuntimeError("reservation exceeds link capacity")
        self.connected = True
        self.reserved_mbps = float(reserve_mbps)
        return True

    @command("disconnect")
    def disconnect(self) -> bool:
        self.connected = False
        self.reserved_mbps = 0.0
        return False

    def status(self) -> Dict[str, Any]:
        return {**super().status(), "connected": self.connected,
                "reserved_mbps": round(self.reserved_mbps, 3),
                "capacity_mbps": round(self.bandwidth_cap_mbps, 3)}


class ServiceSubsystem(Subsystem):
    """Start/stop tracked simulated services."""

    name = "services"

    def __init__(self, services: Optional[Dict[str, bool]] = None) -> None:
        super().__init__()
        self.services: Dict[str, bool] = dict(
            services or {"web": True, "database": True})

    @command("start")
    def start(self, service: str = "") -> bool:
        if service not in self.services:
            raise RuntimeError(f"unknown service '{service}'")
        self.services[service] = True
        return True

    @command("stop")
    def stop(self, service: str = "") -> bool:
        if service not in self.services:
            raise RuntimeError(f"unknown service '{service}'")
        self.services[service] = False
        return False

    @command("list_services")
    def list_services(self) -> Dict[str, bool]:
        return dict(sorted(self.services.items()))

    def status(self) -> Dict[str, Any]:
        running = sorted(k for k, v in self.services.items() if v)
        return {**super().status(), "running": running}


class AuthenticationSubsystem(Subsystem):
    """Account lockout and credential rotation (deterministic)."""

    name = "authentication"

    def __init__(self) -> None:
        super().__init__()
        self.locked: Dict[str, bool] = {}
        self.rotation_counter = 0

    @command("lock_account")
    def lock_account(self, account: str = "") -> bool:
        if not account:
            raise RuntimeError("account required")
        self.locked[account] = True
        return True

    @command("unlock_account")
    def unlock_account(self, account: str = "") -> bool:
        self.locked[account] = False
        return False

    @command("rotate_credentials")
    def rotate_credentials(self, account: str = "system") -> str:
        self.rotation_counter += 1
        digest = hashlib.sha256(
            f"{account}:{self.rotation_counter}".encode()).hexdigest()
        return digest[:12]

    def status(self) -> Dict[str, Any]:
        locked = sorted(a for a, v in self.locked.items() if v)
        return {**super().status(), "locked_accounts": locked,
                "rotations": self.rotation_counter}


class MonitoringSubsystem(Subsystem):
    """Alert queue with severity tracking."""

    name = "monitoring"

    def __init__(self, alert_log_size: int = 50) -> None:
        super().__init__()
        self.alerts: deque = deque(maxlen=alert_log_size)

    @command("raise_alert")
    def raise_alert(self, kind: str = "generic",
                    severity: float = 0.5) -> int:
        self.alerts.append({"kind": str(kind),
                            "severity": round(float(severity), 3)})
        return len(self.alerts)

    @command("acknowledge_alerts")
    def acknowledge_alerts(self) -> int:
        count = len(self.alerts)
        self.alerts.clear()
        return count

    def status(self) -> Dict[str, Any]:
        return {**super().status(), "open_alerts": len(self.alerts)}


class ConfigurationSubsystem(Subsystem):
    """Whitelisted key/value configuration store."""

    name = "configuration"

    DEFAULT_KEYS = ("mode", "log_level", "timeout_s")

    def __init__(self, allowed_keys: Optional[tuple] = None) -> None:
        super().__init__()
        self.allowed = tuple(allowed_keys or self.DEFAULT_KEYS)
        self.values: Dict[str, Any] = {}

    @command("set")
    def set_value(self, key: str = "", value: Any = None) -> Any:
        if key not in self.allowed:
            raise RuntimeError(f"configuration key '{key}' not permitted")
        self.values[key] = value
        return self.values[key]

    @command("get")
    def get_value(self, key: str = "") -> Any:
        if key not in self.allowed:
            raise RuntimeError(f"configuration key '{key}' not permitted")
        return self.values.get(key)

    def status(self) -> Dict[str, Any]:
        return {**super().status(),
                "values": {k: self.values[k]
                           for k in sorted(self.values)}}


class DefensiveControlsSubsystem(Subsystem):
    """Posture control for a SIMULATED node's defensive tooling.

    Postures: ``permissive`` -> ``hardened`` -> ``isolated``. Raising the
    posture restricts the node's own interfaces; quarantining records
    segmented segments. Purely a modeled control plane -- it has no effect
    on, and no connection to, any real system.
    """

    name = "defensive_controls"
    POSTURES = ("permissive", "hardened", "isolated")

    def __init__(self) -> None:
        super().__init__()
        self.posture = "permissive"
        self.quarantined: list = []
        self.hardening_level = 0.0

    @command("set_posture")
    def set_posture(self, level: str = "permissive") -> str:
        if level not in self.POSTURES:
            raise RuntimeError(f"unknown defensive posture '{level}'")
        self.posture = level
        if level == "hardened":
            self.hardening_level = max(self.hardening_level, 0.5)
        elif level == "isolated":
            self.hardening_level = 1.0
        return self.posture

    @command("harden")
    def harden(self, amount: float = 0.25) -> float:
        self.hardening_level = min(1.0, self.hardening_level + float(amount))
        return round(self.hardening_level, 3)

    @command("quarantine_segment")
    def quarantine_segment(self, segment: str = "") -> bool:
        if not segment:
            raise RuntimeError("segment name required")
        if segment not in self.quarantined:
            self.quarantined.append(segment)
        return True

    def status(self) -> Dict[str, Any]:
        return {**super().status(), "posture": self.posture,
                "hardening_level": round(self.hardening_level, 3),
                "quarantined_segments": list(self.quarantined)}
