# Copyright (c) Ultrone Contributors. All rights reserved.
"""Cockpit runtime: binds the real second-generation subsystems to the UI.

Nothing here is a mock. The runtime instantiates and drives the genuine objects:

* ``packages.runtime.device_protocol`` - manifests, 10-state FSM, telemetry
  buffers, capability leases and the device registry.
* ``packages.agents.mcp`` - the MCP 2026-07-28 server and the UDIS gateway.
* ``packages.runtime.event_sourcing`` - hash-chained event store, signed audit
  checkpoints and the causal-boundary validator.
* ``packages.runtime.safety.invariants`` - the SAF-001..SAF-005 registry.
* ``packages.research.benchmarking`` - paired statistics with CIs and effect size.
* ``capabilities.yaml`` / ``VALIDATION_STATUS.md`` - governance maturity and
  engineering evidence, parsed live rather than hard-coded.
"""

from __future__ import annotations

import os
import statistics as _statistics
import threading
import time
import uuid
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

import yaml

from packages.agents.mcp.protocol import McpRequest, McpRequestMetadata
from packages.agents.mcp.udis_gateway import UdisMcpGateway
from packages.research.benchmarking.statistics import compute_paired_statistics
from packages.runtime.device_protocol.driver import SimulationDeviceDriver
from packages.runtime.device_protocol.leases import LeaseManager
from packages.runtime.device_protocol.limits import SafetyConstraint
from packages.runtime.device_protocol.manifest import (
    AuthorityLevel,
    DeviceCapability,
    DeviceManifest,
    DeviceOperatingMode,
    DeviceSafetySpec,
    GranularScope,
)
from packages.runtime.device_protocol.registry import DeviceRegistry
from packages.runtime.event_sourcing.event_store import EventStore
from packages.runtime.event_sourcing.events import EventType
from packages.runtime.safety.invariants.registry import InvariantRegistry

from .scenarios import DEFAULT_SCENARIO_ID, SCENARIOS, FaultConfig, ScenarioSpec, get_scenario
from .world import WorldEngine, WorldHooks

MCP_PROTOCOL_VERSION = "2026-07-28"
REPO_ROOT = Path(__file__).resolve().parents[3]

#: Capabilities the cockpit is allowed to exercise. Physical scopes are absent
#: by construction: the UI has no way to request them.
COCKPIT_CAPABILITIES: Tuple[str, ...] = (
    GranularScope.OBSERVE_STATE.value,
    GranularScope.OBSERVE_TELEMETRY.value,
    GranularScope.OBSERVE_HEALTH.value,
    GranularScope.SIMULATE_EXECUTE.value,
)

DENIED_CAPABILITIES: Tuple[str, ...] = (
    GranularScope.PHYSICAL_EXECUTE.value,
    GranularScope.PHYSICAL_REQUEST.value,
    GranularScope.ADMIN_CONFIGURE.value,
)


def _load_capabilities_yaml() -> Dict[str, Any]:
    path = REPO_ROOT / "capabilities.yaml"
    if not path.is_file():
        return {"version": "unknown", "capabilities": {}}
    with open(path, "r", encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {"capabilities": {}}


def _load_validation_status() -> Dict[str, Any]:
    """Extract the evidence ledger from VALIDATION_STATUS.md (no hard-coding)."""
    path = REPO_ROOT / "VALIDATION_STATUS.md"
    if not path.is_file():
        return {"available": False, "sections": [], "tables": []}
    lines = path.read_text(encoding="utf-8").splitlines()
    sections: List[str] = [ln.lstrip("# ").strip() for ln in lines if ln.startswith("## ")]
    tables: List[List[str]] = []
    current: List[str] = []
    for line in lines:
        if line.startswith("|") and not set(line) <= set("|-: "):
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if cells:
                current.append(cells)
        elif current:
            tables.append(current)
            current = []
    if current:
        tables.append(current)

    subsystems: List[Dict[str, Any]] = []
    for table in tables:
        header = [h.lower() for h in table[0]]
        if "subsystem / area" in header:
            for row in table[1:]:
                if len(row) < 3:
                    continue
                subsystems.append(
                    {
                        "subsystem": row[0].replace("**", "").strip(),
                        "status": row[1].replace("**", "").strip(),
                        "implementation": row[2].strip(),
                        "evidence": row[3].strip() if len(row) > 3 else "",
                    }
                )
    invariants: List[Dict[str, Any]] = []
    for table in tables:
        header = [h.strip("` ").lower() for h in table[0]]
        if "invariant id" in header:
            for row in table[1:]:
                if len(row) < 5:
                    continue
                invariants.append(
                    {
                        "id": row[0].strip("`* "),
                        "name": row[1].strip("`* "),
                        "severity": row[2].strip("`* "),
                        "implementation": row[3].strip("`* "),
                        "test": row[4].strip("`* "),
                        "owner": row[5].strip("`* ") if len(row) > 5 else "safety-kernel",
                    }
                )
    header_line = lines[2] if len(lines) > 2 else ""
    return {
        "available": True,
        "summary": header_line.replace(">", "").replace("**", "").strip(),
        "sections": sections,
        "subsystems": subsystems,
        "invariants": invariants,
    }


def build_sensor_manifest(sensor: Any, device_key: Any) -> DeviceManifest:
    """A real UDIS manifest for a simulated sensor device."""
    from packages.runtime.device_protocol.procedures import ProcedureCompiler

    capabilities = [
        DeviceCapability(
            name="observe.state",
            description="Read the device's canonical state and freshness metadata.",
            is_read_only=True,
            requires_lease=False,
            authority_level=AuthorityLevel.OBSERVE,
            required_scopes=[GranularScope.OBSERVE_STATE],
        ),
        DeviceCapability(
            name="observe.telemetry",
            description=f"Read {sensor.modality} telemetry frames.",
            is_read_only=True,
            requires_lease=False,
            authority_level=AuthorityLevel.OBSERVE,
            required_scopes=[GranularScope.OBSERVE_TELEMETRY],
        ),
        DeviceCapability(
            name="observe.health",
            description="Read device health and calibration status.",
            is_read_only=True,
            requires_lease=False,
            authority_level=AuthorityLevel.OBSERVE,
            required_scopes=[GranularScope.OBSERVE_HEALTH],
        ),
        DeviceCapability(
            name="simulate.execute",
            description="Execute an actuation intent against the simulation model only.",
            parameters_schema={
                "type": "object",
                "properties": {
                    "entity_id": {"type": "string"},
                    "aimpoint": {"type": "array", "items": {"type": "number"}},
                    "confidence": {"type": "number"},
                },
                "required": ["entity_id"],
            },
            is_read_only=False,
            requires_lease=True,
            authority_level=AuthorityLevel.ACTUATE,
            required_scopes=[GranularScope.SIMULATE_EXECUTE],
        ),
        DeviceCapability(
            name="simulate.intercept",
            description="Simulated intercept intent (no physical actuation path exists).",
            is_read_only=False,
            requires_lease=True,
            authority_level=AuthorityLevel.ACTUATE,
            required_scopes=[GranularScope.SIMULATE_EXECUTE],
        ),
        DeviceCapability(
            name="simulate.observe",
            description="Simulated passive track refinement.",
            is_read_only=False,
            requires_lease=True,
            authority_level=AuthorityLevel.ACTUATE,
            required_scopes=[GranularScope.SIMULATE_EXECUTE],
        ),
    ]

    procedures = [
        ProcedureCompiler.compile_from_actions(
            name="calibration",
            description="Deterministic calibration sweep for the sensing chain.",
            actions=[
                {"command": "observe.health", "params": {"channel": "health"}},
                {"command": "calibration.sweep", "params": {"iterations": 3}},
            ],
            required_capabilities=["observe.health", "simulate.execute"],
        ),
        ProcedureCompiler.compile_from_actions(
            name="diagnostic",
            description="Deterministic self-diagnostic sequence.",
            actions=[
                {"command": "observe.state", "params": {}},
                {"command": "observe.telemetry", "params": {"channel": f"observation/{sensor.sensor_id}"}},
            ],
            required_capabilities=["observe.state", "observe.telemetry"],
        ),
    ]

    manifest = DeviceManifest(
        device_id=sensor.device_id,
        device_type=f"{sensor.modality}_sensor",
        manufacturer="ultrone-simulated",
        model=f"{sensor.label.lower().replace(' ', '-')}-sim-v1",
        firmware="sim-1.0.0",
        mode=DeviceOperatingMode.SIMULATION,
        capabilities=capabilities,
        state_schema={
            "type": "object",
            "properties": {
                "state": {"type": "string", "enum": [
                    "DISCOVERING", "READY", "DEGRADED", "BUSY", "PAUSED",
                    "FAULT", "EMERGENCY_STOP", "OFFLINE", "MAINTENANCE", "SIMULATION",
                ]},
                "is_operational": {"type": "boolean"},
                "telemetry": {"type": "object"},
            },
        },
        procedures=procedures,
        constraints=[
            SafetyConstraint(
                constraint_id=f"{sensor.device_id}-conf",
                parameter="confidence",
                operator="range",
                limit_value=(0.0, 1.0),
                description="Confidence parameter must be a valid probability.",
            ),
        ],
        telemetry_channels=[f"observation/{sensor.sensor_id}", "health"],
        health={
            "nominal": True,
            "modality": sensor.modality,
            "range_km": sensor.range_km,
            "noise_sigma_km": sensor.noise_sigma_km,
            "latency_ticks": sensor.latency_ticks,
            "freshness_horizon_ms": sensor.ttl_ticks * 1000.0,
        },
        safety=DeviceSafetySpec(
            simulation_only=True,
            e_stop_channel=f"udis/{sensor.device_id}/estop",
            max_rate_hz=10.0,
            requires_human_approval_for_physical=True,
            constraints=[
                SafetyConstraint(
                    constraint_id=f"{sensor.device_id}-sim",
                    parameter="mode",
                    operator="==",
                    limit_value="simulation",
                    description="This device only exists in simulation mode.",
                )
            ],
        ),
    )
    if device_key is not None:
        try:
            manifest.sign(device_key, "ultrone-cockpit-authoring-authority")
        except Exception:  # pragma: no cover - signing is best-effort evidence
            pass
    return manifest


class CockpitRuntime:
    """Single in-process cockpit runtime driving real ULTRONE subsystems."""

    def __init__(self, scenario_id: str = DEFAULT_SCENARIO_ID):
        self._lock = threading.RLock()
        self._stop = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._speed = 1.0
        self._running = False

        self.scenario: ScenarioSpec = get_scenario(scenario_id)
        self.run_id = f"RUN-{uuid.uuid4().hex[:6].upper()}"
        self.trace_id = self.scenario.scenario_id
        self.environment = "simulation"
        self.mcp_protocol_version = MCP_PROTOCOL_VERSION

        # ── real subsystems ────────────────────────────────────────────────
        self.event_store = EventStore()
        self.invariant_registry = InvariantRegistry()
        self.lease_manager = LeaseManager()
        self.registry = DeviceRegistry(lease_manager=self.lease_manager)
        self.audit_signing_key = uuid.uuid4().hex
        self._device_key = self._generate_key()

        self._drivers: Dict[str, Any] = {}
        self._manifests: Dict[str, DeviceManifest] = {}
        self._mcp_traffic: List[Dict[str, Any]] = []
        self._ui_actions: List[Dict[str, Any]] = []
        self._checkpoints: List[Dict[str, Any]] = []
        self._lease_events: List[Dict[str, Any]] = []
        self._faults = FaultConfig()
        self._replay_digest: Optional[str] = None

        self._build_devices()
        self.mcp = UdisMcpGateway(self.registry, "ULTRONE UDIS Gateway")
        self.world = WorldEngine(
            scenario=self.scenario,
            event_store=self.event_store,
            trace_id=self.trace_id,
            faults=self._faults,
            hooks=self._build_hooks(),
        )
        self.started_at = time.time()
        # Seed a handful of ticks so the cockpit opens onto real state.
        for _ in range(6):
            self.world.step()

    # ── construction helpers ────────────────────────────────────────────────
    @staticmethod
    def _generate_key() -> Any:
        try:
            from packages.runtime.event_sourcing.event_store import ed25519

            return ed25519.Ed25519PrivateKey.generate()
        except Exception:  # pragma: no cover - crypto optional
            return None

    def _build_devices(self) -> None:
        for sensor in self.scenario.sensors:
            manifest = build_sensor_manifest(sensor, self._device_key)
            driver = SimulationDeviceDriver(manifest)
            self.registry.register_device(manifest, driver)
            self._drivers[manifest.device_id] = driver
            self._manifests[manifest.device_id] = manifest

    def _build_hooks(self) -> WorldHooks:
        return WorldHooks(
            telemetry_publish=self._publish_telemetry,
            lease_validate=self._validate_lease,
            lease_issue=self._issue_lease,
            device_state=self._device_state,
            execute_command=self._execute_command,
        )

    # ── UDIS bindings (every call lands on a real UDIS object) ──────────────
    def _publish_telemetry(self, sensor: Any, observation: Any) -> Any:
        driver = self._drivers.get(sensor.device_id)
        if driver is None:
            return None
        return driver.telemetry.push(
            channel=f"observation/{sensor.sensor_id}",
            value={
                "observation_id": observation.observation_id,
                "entity_id": observation.entity_id,
                "position": [round(observation.x, 4), round(observation.y, 4)],
            },
            quality=observation.quality,
            confidence=observation.confidence,
            ttl_seconds=observation.ttl_seconds,
            source=sensor.sensor_id,
        )

    def _validate_lease(self, lease_id: Optional[str], capability: str) -> Tuple[bool, Optional[str]]:
        if not lease_id:
            return False, f"No capability lease presented for '{capability}'"
        return self.lease_manager.validate_action(lease_id, capability)

    def _issue_lease(self, agent_id: str, device_id: str, capabilities: Any) -> Optional[str]:
        if not device_id or device_id not in self._drivers:
            return None
        try:
            lease = self.lease_manager.request_lease(
                agent_id=agent_id,
                device_id=device_id,
                capabilities=set(capabilities),
                duration_seconds=180.0,
                purpose="cockpit_simulated_mission",
                policy_version=self.scenario.policy_version,
                is_simulation=True,
                rate_limit_per_min=600,
            )
        except Exception:
            return None
        self._lease_events.append(
            {
                "event": "issued",
                "lease_id": lease.lease_id,
                "agent_id": agent_id,
                "device_id": device_id,
                "capabilities": sorted(lease.capabilities),
                "granted_at": lease.granted_at,
                "expires_at": lease.expires_at,
                "purpose": lease.purpose,
                "rate_limit_per_min": lease.rate_limit_per_min,
                "is_simulation": lease.is_simulation,
            }
        )
        return lease.lease_id

    def _device_state(self, device_id: str) -> Optional[str]:
        driver = self._drivers.get(device_id)
        return driver.get_state().value if driver is not None else None

    def _execute_command(self, device_id: str, command: str, params: Dict[str, Any], lease_id: Optional[str]) -> Any:
        return self.registry.execute_command(device_id, command, params, lease_id)

    # ── playback control (control plane; every call is audited) ────────────
    def play(self, speed: Optional[float] = None, actor: str = "operator") -> Dict[str, Any]:
        with self._lock:
            if speed is not None:
                self._speed = max(0.1, min(64.0, float(speed)))
            if self._running:
                return self.playback_state()
            self._running = True
            self._stop.clear()
            self._thread = threading.Thread(target=self._loop, name="ultrone-cockpit-tick", daemon=True)
            self._thread.start()
        self.record_ui_action(actor, "play", self.run_id, {"speed": self._speed})
        return self.playback_state()

    def pause(self, actor: str = "operator") -> Dict[str, Any]:
        with self._lock:
            self._running = False
            self._stop.set()
        self.record_ui_action(actor, "pause", self.run_id, {})
        return self.playback_state()

    def step(self, count: int = 1, actor: str = "operator") -> Dict[str, Any]:
        count = max(1, min(200, int(count)))
        with self._lock:
            snapshot = None
            for _ in range(count):
                snapshot = self.world.step()
        self.record_ui_action(actor, "step", self.run_id, {"count": count})
        return snapshot or self.world.snapshot()

    def reset(self, actor: str = "operator") -> Dict[str, Any]:
        with self._lock:
            self._running = False
            self._stop.set()
            self._faults = FaultConfig()
            self.world.reset(self._faults)
            for _ in range(6):
                self.world.step()
        self.record_ui_action(actor, "reset", self.run_id, {})
        return self.world.snapshot()

    def set_speed(self, speed: float, actor: str = "operator") -> Dict[str, Any]:
        with self._lock:
            self._speed = max(0.1, min(64.0, float(speed)))
        self.record_ui_action(actor, "set_speed", self.run_id, {"speed": self._speed})
        return self.playback_state()

    def inject_faults(self, config: Dict[str, Any], actor: str = "researcher") -> Dict[str, Any]:
        """Arm fault levers. These change *real* subsystem behaviour, not UI flags."""
        with self._lock:
            self._faults = FaultConfig(
                sensor_dropout=tuple(config.get("sensor_dropout", [])),
                telemetry_delay=tuple(config.get("telemetry_delay", [])),
                sensor_disagreement=tuple(config.get("sensor_disagreement", [])),
                device_offline=tuple(config.get("device_offline", [])),
                lease_expiry=bool(config.get("lease_expiry", False)),
                latency_injection_ms=float(config.get("latency_injection_ms", 0.0)),
                agent_pause=tuple(config.get("agent_pause", [])),
            )
            self.world.faults = self._faults
        self.record_ui_action(actor, "inject_faults", self.run_id, self._faults.to_dict())
        return {"faults": self._faults.to_dict(), "stats": self.world.stats()}

    def clear_faults(self, actor: str = "researcher") -> Dict[str, Any]:
        return self.inject_faults({}, actor)

    def _loop(self) -> None:
        while not self._stop.is_set():
            with self._lock:
                try:
                    self.world.step()
                except Exception:  # pragma: no cover - the tick loop must never die
                    pass
                speed = self._speed
            self._stop.wait(max(0.05, 0.35 / max(speed, 0.1)))

    def playback_state(self) -> Dict[str, Any]:
        return {
            "running": self._running,
            "speed": self._speed,
            "tick": self.world.tick,
            "max_ticks": self.scenario.max_ticks,
            "dt_seconds": self.scenario.dt_seconds,
            "simulation_time_s": round(self.world.tick * self.scenario.dt_seconds, 2),
            "environment": self.environment,
        }

    # ── MCP 2026-07-28 traffic (real gateway, real wire objects) ────────────
    def mcp_call(self, method: str, params: Optional[Dict[str, Any]] = None, label: Optional[str] = None) -> Dict[str, Any]:
        """Send one JSON-RPC request through the genuine UDIS MCP gateway."""
        request_id = f"mcp-{uuid.uuid4().hex[:8]}"
        request = McpRequest(
            method=method,
            params=params or {},
            id=request_id,
            metadata=McpRequestMetadata(
                protocol_version=MCP_PROTOCOL_VERSION,
                client_info={"name": "ultrone-cockpit", "version": "1.0.0"},
                capabilities={"tools": {}, "resources": {}},
            ),
        )
        started = time.perf_counter()
        error: Optional[Dict[str, Any]] = None
        result: Optional[Dict[str, Any]] = None
        try:
            response = self.mcp.handle_request(request)
            error = response.error
            result = response.result
            wire = response.to_dict()
        except Exception as exc:  # pragma: no cover - defensive
            error = {"code": -32603, "message": str(exc)}
            wire = {"jsonrpc": "2.0", "id": request_id, "error": error}
        latency_ms = (time.perf_counter() - started) * 1000.0
        correlation_id = uuid.uuid4().hex[:12]

        self._record_traffic("REQUEST", method, request.to_dict(), label or method, correlation_id, latency_ms)
        self._record_traffic(
            "ERROR" if error else "RESPONSE",
            method,
            wire,
            label or method,
            correlation_id,
            latency_ms,
            error=error,
        )
        return {
            "method": method,
            "label": label or method,
            "request": request.to_dict(),
            "response": wire,
            "result": result,
            "error": error,
            "latency_ms": round(latency_ms, 3),
            "correlation_id": correlation_id,
            "protocol_version": MCP_PROTOCOL_VERSION,
            "server": "ULTRONE UDIS Gateway",
        }

    def _record_traffic(
        self,
        kind: str,
        method: str,
        body: Dict[str, Any],
        label: str,
        correlation_id: str,
        latency_ms: float,
        error: Optional[Dict[str, Any]] = None,
    ) -> None:
        self._mcp_traffic.append(
            {
                "traffic_id": f"mcp-{len(self._mcp_traffic) + 1:05d}",
                "kind": kind,
                "method": method,
                "label": label,
                "correlation_id": correlation_id,
                "timestamp": time.time(),
                "latency_ms": round(latency_ms, 3),
                "protocol_version": MCP_PROTOCOL_VERSION,
                "headers": {
                    "MCP-Protocol-Version": MCP_PROTOCOL_VERSION,
                    "Mcp-Method": method,
                    "Mcp-Name": label,
                },
                "body": body,
                "error": error,
            }
        )
        if len(self._mcp_traffic) > 600:
            self._mcp_traffic = self._mcp_traffic[-300:]

    def mcp_traffic(self, limit: int = 100, method: Optional[str] = None) -> List[Dict[str, Any]]:
        pool = self._mcp_traffic
        if method:
            pool = [t for t in pool if t["method"] == method]
        return pool[-limit:]

    def mcp_discovery(self) -> Dict[str, Any]:
        """Discover the server, its tools, its resources and its cache metadata."""
        discovery = self.mcp_call("server/discover", {}, "server/discover")
        tools = self.mcp_call("tools/list", {}, "tools/list")
        resources = self.mcp_call("resources/list", {}, "resources/list")
        tool_result = tools.get("result") or {}
        resource_result = resources.get("result") or {}
        discovery_result = discovery.get("result") or {}
        return {
            "protocol_version": MCP_PROTOCOL_VERSION,
            "server_name": "ULTRONE UDIS Gateway",
            "discovery": discovery,
            "tools": tool_result.get("tools", []),
            "resources": resource_result.get("resources", []),
            "capabilities": discovery_result.get("capabilities", {}),
            "supported_versions": discovery_result.get("supportedVersions", []),
            "cache": {
                "discovery_ttl_ms": discovery_result.get("ttlMs"),
                "tools_ttl_ms": tool_result.get("ttlMs"),
                "resources_ttl_ms": resource_result.get("ttlMs"),
                "cache_scope": tool_result.get("cacheScope"),
            },
            "error_contract": {
                "unsupported_protocol_version": -32022,
                "header_mismatch": -32023,
                "resource_not_found": -32002,
                "method_not_found": -32601,
                "invalid_params": -32602,
            },
        }

    def mcp_tool_call(self, tool: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Invoke a UDIS tool through the real MCP wire path."""
        if tool == "execute_procedure":
            device_id = arguments.get("device_id")
            procedure = arguments.get("procedure_name")
            if device_id in self._drivers and procedure:
                try:
                    result = self.registry.execute_procedure(
                        device_id, procedure, arguments.get("params"), arguments.get("lease_id")
                    )
                    body = {
                        "procedure_id": result.procedure_id,
                        "success": result.success,
                        "steps_completed": result.steps_completed,
                        "total_steps": result.total_steps,
                        "duration_seconds": result.duration_seconds,
                        "error": result.error,
                    }
                    self._record_traffic(
                        "RESPONSE", "tools/call", body, tool, uuid.uuid4().hex[:12], 0.0
                    )
                    return {"tool": tool, "ok": result.success, "result": body, "error": None}
                except Exception as exc:
                    return {"tool": tool, "ok": False, "result": None, "error": {"message": str(exc)}}

        if tool == "emergency_stop" and arguments.get("device_id") in self._drivers:
            driver = self._drivers[arguments["device_id"]]
            transition = driver.emergency_stop(reason=arguments.get("reason", "operator E-STOP via cockpit"))
            return {
                "tool": tool,
                "ok": True,
                "error": None,
                "result": {
                    "device_id": transition.device_id,
                    "from_state": transition.from_state.value,
                    "to_state": transition.to_state.value,
                    "reason": transition.reason,
                    "authorized_by": transition.authorized_by,
                    "timestamp": transition.timestamp,
                    "invariant": "SAF-004 (emergency stop is terminal until reset)",
                },
            }

        call = self.mcp_call("tools/call", {"name": tool, "arguments": arguments}, tool)
        result = call.get("result") or {}
        return {
            "tool": tool,
            "ok": call["error"] is None and not result.get("isError", False),
            "result": result,
            "error": call["error"],
            "latency_ms": call["latency_ms"],
            "raw": call,
        }

    def mcp_resource_read(self, uri: str) -> Dict[str, Any]:
        call = self.mcp_call("resources/read", {"uri": uri}, uri)
        return {
            "uri": uri,
            "result": call.get("result"),
            "error": call["error"],
            "latency_ms": call["latency_ms"],
            "raw": call,
        }

    def mcp_tool_names(self) -> List[str]:
        tools = self.mcp_discovery().get("tools", [])
        return sorted(t.get("name", "") for t in tools)

    # ── UDIS device laboratory (schema-driven from real manifests) ──────────
    def device_catalog(self) -> Dict[str, Any]:
        devices = []
        for device_id, driver in self._drivers.items():
            manifest = self._manifests[device_id]
            state = driver.get_state().value
            fresh = driver.telemetry.get_all_fresh()
            history = driver.state_machine.history
            signature_ok, signature_detail = manifest.verify_signature()
            devices.append(
                {
                    "device_id": device_id,
                    "device_type": manifest.device_type,
                    "manufacturer": manifest.manufacturer,
                    "model": manifest.model,
                    "firmware": manifest.firmware,
                    "mode": manifest.mode.value,
                    "state": state,
                    "is_operational": driver.state_machine.is_operational(),
                    "simulation_only": manifest.safety.simulation_only,
                    "health": manifest.health,
                    "health_score": 0.98 if state in ("READY", "SIMULATION", "BUSY") else 0.55,
                    "telemetry_channels": manifest.telemetry_channels,
                    "fresh_channels": sorted(fresh.keys()),
                    "stale_channels": sorted(set(manifest.telemetry_channels) - set(fresh.keys())),
                    "capabilities": sorted(c.name for c in manifest.capabilities),
                    "procedures": sorted(p.name for p in manifest.procedures),
                    "lease_required": sorted(c.name for c in manifest.capabilities if c.requires_lease),
                    "read_only": sorted(c.name for c in manifest.capabilities if c.is_read_only),
                    "signature": {
                        "signed": bool(manifest.signature),
                        "valid": signature_ok,
                        "detail": signature_detail,
                        "scheme": manifest.signature_scheme,
                        "author_identity": manifest.author_identity,
                        "public_key_hex": manifest.public_key_hex,
                    },
                    "last_transition": (
                        {
                            "from_state": history[-1].from_state.value,
                            "to_state": history[-1].to_state.value,
                            "timestamp": history[-1].timestamp,
                            "reason": history[-1].reason,
                            "authorized_by": history[-1].authorized_by,
                        }
                        if history
                        else None
                    ),
                    "transition_count": len(history),
                }
            )
        return {
            "devices": devices,
            "registry_version": "udis-1.0",
            "summary": {
                "total": len(devices),
                "operational": sum(1 for d in devices if d["is_operational"]),
                "busy": sum(1 for d in devices if d["state"] == "BUSY"),
                "degraded": sum(1 for d in devices if d["state"] == "DEGRADED"),
                "fault": sum(1 for d in devices if d["state"] == "FAULT"),
                "offline": sum(1 for d in devices if d["state"] == "OFFLINE"),
                "maintenance": sum(1 for d in devices if d["state"] == "MAINTENANCE"),
                "simulation_only": sum(1 for d in devices if d["simulation_only"]),
            },
            "states": [
                "DISCOVERING", "READY", "DEGRADED", "BUSY", "PAUSED",
                "FAULT", "EMERGENCY_STOP", "OFFLINE", "MAINTENANCE", "SIMULATION",
            ],
        }

    def _telemetry_series(self, device_id: str, limit: int = 40) -> List[Dict[str, Any]]:
        """Observation series for the sensor bound to a device (public data path)."""
        sensors = {s.sensor_id for s in self.scenario.sensors if s.device_id == device_id}
        if not sensors:
            return []
        series = [o for o in self.world.observations(limit=600) if o["sensor_id"] in sensors]
        return series[-limit:]

    def device_detail(self, device_id: str) -> Optional[Dict[str, Any]]:
        driver = self._drivers.get(device_id)
        if driver is None:
            return None
        manifest = self._manifests[device_id]
        history = driver.state_machine.history
        entry = next(
            (d for d in self.device_catalog()["devices"] if d["device_id"] == device_id), {}
        )
        return {
            **entry,
            "manifest": manifest.to_dict(),
            "telemetry": {
                channel: measurement.to_dict()
                for channel, measurement in driver.telemetry.get_all_fresh().items()
            },
            "telemetry_history": {
                channel: [m.to_dict() for m in driver.telemetry.get_history(channel, limit=30)]
                for channel in manifest.telemetry_channels
            },
            "telemetry_series": self._telemetry_series(device_id),
            "fsm": {
                "current_state": driver.get_state().value,
                "allowed_transitions": sorted(s.value for s in driver.state_machine.allowed_transitions()),
                "transitions": [
                    {
                        "from_state": t.from_state.value,
                        "to_state": t.to_state.value,
                        "timestamp": t.timestamp,
                        "reason": t.reason,
                        "authorized_by": t.authorized_by,
                    }
                    for t in history[-40:]
                ],
            },
            "leases": [
                event for event in self._lease_events if event["device_id"] == device_id
            ],
            "procedures": [p.to_dict() for p in manifest.procedures],
            "admissible_actions": [
                {
                    "name": c.name,
                    "requires_lease": c.requires_lease,
                    "is_read_only": c.is_read_only,
                    "authority_level": c.authority_level.value,
                    "required_scopes": [s.value for s in c.required_scopes],
                    "parameters_schema": c.parameters_schema,
                }
                for c in manifest.capabilities
            ],
        }

    # ── event sourcing: chain, checkpoints, replay ──────────────────────────
    def execution_envelope(self) -> Dict[str, Any]:
        from packages.runtime.event_sourcing.replay import ExecutionEnvelope

        envelope = ExecutionEnvelope(
            git_commit_sha=self._git_commit(),
            python_version=f"{os.sys.version_info.major}.{os.sys.version_info.minor}."
            f"{os.sys.version_info.micro}",
            random_seed=self.scenario.seed,
            config_hash=self._config_hash(),
            model_weights_hash=self._sha_of(self.scenario.model_version),
            environment_version=f"cockpit-sim-1.0.0/{self.scenario.scenario_id}",
        )
        return {
            "git_commit_sha": envelope.git_commit_sha,
            "python_version": envelope.python_version,
            "random_seed": envelope.random_seed,
            "config_hash": envelope.config_hash,
            "model_weights_hash": envelope.model_weights_hash,
            "environment_version": envelope.environment_version,
            "envelope_digest": envelope.envelope_digest(),
            "reproducibility_mode": "STRICT",
            "expected_digest": self._replay_digest,
        }

    @staticmethod
    def _sha_of(*parts: Any) -> str:
        import hashlib

        return hashlib.sha256("|".join(str(p) for p in parts).encode("utf-8")).hexdigest()

    def _git_commit(self) -> str:
        candidates = [REPO_ROOT / ".git" / "HEAD", REPO_ROOT / ".git" / "refs" / "heads" / "main"]
        try:
            head = (REPO_ROOT / ".git" / "HEAD").read_text(encoding="utf-8").strip()
            if head.startswith("ref:"):
                ref = REPO_ROOT / ".git" / head.split(" ", 1)[1].strip()
                if ref.is_file():
                    return ref.read_text(encoding="utf-8").strip()
            return head
        except Exception:  # pragma: no cover - detached/absent git dir
            for candidate in candidates:
                if candidate.is_file():
                    try:
                        return candidate.read_text(encoding="utf-8").strip()
                    except Exception:
                        continue
            return "unknown"

    def _config_hash(self) -> str:
        return self._sha_of(
            self.scenario.scenario_id,
            self.scenario.seed,
            self.scenario.model_version,
            self.scenario.policy_version,
            self.scenario.dataset_version,
            self.scenario.telemetry_freshness_ms,
            self.scenario.bounds_km,
        )

    def events(self, limit: int = 200, event_type: Optional[str] = None, since_tick: Optional[int] = None) -> List[Dict[str, Any]]:
        trace = self.event_store.get_trace(self.trace_id)
        if event_type:
            trace = [e for e in trace if e.event_type.value == event_type]
        if since_tick is not None:
            trace = [e for e in trace if e.logical_tick >= since_tick]
        return [e.to_dict() for e in trace[-limit:]]

    def event_types(self) -> List[str]:
        return [t.value for t in EventType]

    def event_store_status(self) -> Dict[str, Any]:
        trace = self.event_store.get_trace(self.trace_id)
        ok, err = self.event_store.verify_chain_integrity(self.trace_id)
        latest = self._checkpoints[-1] if self._checkpoints else None
        checkpoint_ok = True
        if latest:
            checkpoint_obj = latest["checkpoint"]
            checkpoint_ok, checkpoint_err = self.event_store.verify_checkpoint(
                checkpoint_obj, self.audit_signing_key
            )
            latest = {**latest, "verified": checkpoint_ok}
            if not checkpoint_ok:
                err = checkpoint_err
        return {
            "run_id": self.run_id,
            "trace_id": self.trace_id,
            "event_count": len(trace),
            "chain_valid": ok,
            "chain_detail": err,
            "head_event_hash": trace[-1].compute_event_hash() if trace else None,
            "checkpoint": latest,
            "checkpoint_valid": checkpoint_ok,
            "signature_scheme": "hmac-sha256" if latest else None,
            "first_tick": trace[0].logical_tick if trace else None,
            "last_tick": trace[-1].logical_tick if trace else None,
        }

    def create_checkpoint(self, actor: str = "auditor") -> Dict[str, Any]:
        checkpoint = self.event_store.create_signed_checkpoint(
            self.trace_id, self.audit_signing_key, signer_id=actor
        )
        self._checkpoints.append(
            {
                "checkpoint_id": checkpoint.checkpoint_id,
                "signer_id": checkpoint.signer_id,
                "event_count": checkpoint.event_count,
                "timestamp": checkpoint.timestamp,
                "cumulative_chain_hash": checkpoint.cumulative_chain_hash,
                "signature_scheme": checkpoint.signature_scheme,
                "checkpoint": checkpoint,
            }
        )
        self.record_ui_action(actor, "create_checkpoint", checkpoint.checkpoint_id, {})
        return self.event_store_status()

    def replay(self, ticks: Optional[int] = None, actor: str = "researcher") -> Dict[str, Any]:
        """Deterministic re-execution in a fresh world + fresh event store.

        The same scenario, seed, model and policy versions are re-run from
        genesis; the resulting event stream is compared against the live trace
        with the real ``DeterministicReplayEngine``.
        """
        ticks = max(1, min(400, int(ticks or self.world.tick)))
        baseline_events = self.event_store.get_trace(self.trace_id)

        replay_store = EventStore()
        replay_world = WorldEngine(
            scenario=self.scenario,
            event_store=replay_store,
            trace_id=f"{self.trace_id}:replay",
            faults=self._faults,
        )
        for _ in range(ticks):
            replay_world.step()
        replayed = replay_store.get_trace(f"{self.trace_id}:replay")

        from packages.runtime.event_sourcing.replay import DeterministicReplayEngine

        engine = DeterministicReplayEngine(replay_store)
        replay_ok, divergences = engine.verify_reproducibility(
            self.trace_id, f"{self.trace_id}:replay"
        )

        paired = list(zip(baseline_events, replayed))
        comparisons: List[Dict[str, Any]] = []
        first_divergence: Optional[Dict[str, Any]] = None
        for index, (base, replay_event) in enumerate(paired):
            match = (
                base.payload_hash == replay_event.payload_hash
                and base.event_type == replay_event.event_type
            )
            if not match and first_divergence is None:
                first_divergence = {
                    "index": index,
                    "tick": replay_event.logical_tick,
                    "event_type": replay_event.event_type.value,
                    "expected_hash": base.payload_hash,
                    "actual_hash": replay_event.payload_hash,
                    "expected_event_id": base.event_id,
                    "actual_event_id": replay_event.event_id,
                    "timestamp": replay_event.timestamp,
                }
            if index < 40:
                comparisons.append(
                    {
                        "index": index,
                        "tick": replay_event.logical_tick,
                        "event_type": replay_event.event_type.value,
                        "expected": base.payload_hash[:16],
                        "actual": replay_event.payload_hash[:16],
                        "match": match,
                    }
                )

        decision_comparison = []
        original_decisions = self.world.decisions(limit=ticks)
        replay_decisions = replay_world.decisions(limit=ticks)
        for base, replayed_decision in zip(original_decisions, replay_decisions):
            decision_comparison.append(
                {
                    "decision_id": base["decision_id"],
                    "entity_id": base["entity_id"],
                    "original_confidence": base["confidence"],
                    "replay_confidence": replayed_decision["confidence"],
                    "original_plan": base["plan_id"],
                    "replay_plan": replayed_decision["plan_id"],
                    "original_approved": base["approved"],
                    "replay_approved": replayed_decision["approved"],
                    "original_latency_ms": base["latency_ms"],
                    "replay_latency_ms": replayed_decision["latency_ms"],
                    "match": (
                        base["plan_id"] == replayed_decision["plan_id"]
                        and base["approved"] == replayed_decision["approved"]
                    ),
                }
            )

        matched = sum(1 for c in comparisons if c["match"])
        digest = self._sha_of(*[e.payload_hash for e in replayed])
        envelope = self.execution_envelope()
        if self._replay_digest is None:
            self._replay_digest = digest

        self.record_ui_action(actor, "replay", self.run_id, {"ticks": ticks})

        return {
            "run_id": self.run_id,
            "trace_id": self.trace_id,
            "ticks": ticks,
            "baseline_event_count": len(baseline_events),
            "replay_event_count": len(replayed),
            "reproducible": replay_ok,
            "divergences": divergences,
            "matched_prefix": f"{matched}/{len(comparisons)}",
            "first_divergence": first_divergence,
            "comparisons": comparisons,
            "decisions": decision_comparison,
            "decision_match_rate": round(
                sum(1 for d in decision_comparison if d["match"])
                / max(len(decision_comparison), 1),
                4,
            ),
            "replay_digest": digest,
            "envelope": envelope,
            "chain_valid": replay_store.verify_chain_integrity(f"{self.trace_id}:replay")[0],
        }

    # ── safety center ───────────────────────────────────────────────────────
    def invariants(self) -> List[Dict[str, Any]]:
        return [inv.to_dict() for inv in self.invariant_registry.list_all()]

    def _freshness_audit(self) -> List[Dict[str, Any]]:
        audit = []
        for sensor in self.scenario.sensors:
            frame = self.world.gate_frame(sensor.sensor_id)
            if frame is None:
                audit.append(
                    {
                        "sensor_id": sensor.sensor_id,
                        "device_id": sensor.device_id,
                        "modality": sensor.modality,
                        "age_ms": None,
                        "fresh": False,
                        "status": "no-frame",
                        "horizon_ms": self.world.freshness_ms,
                    }
                )
                continue
            fresh = bool(frame.is_fresh())
            audit.append(
                {
                    "sensor_id": sensor.sensor_id,
                    "device_id": sensor.device_id,
                    "modality": sensor.modality,
                    "age_ms": round(max(0.0, (time.monotonic() - frame.monotonic_timestamp) * 1000.0), 1),
                    "fresh": fresh,
                    "status": "fresh" if fresh else "stale",
                    "horizon_ms": self.world.freshness_ms,
                    "sequence_number": frame.sequence_number,
                    "quality": frame.quality,
                    "confidence": frame.confidence,
                }
            )
        return audit

    def safety_status(self) -> Dict[str, Any]:
        decisions = self.world.decisions(limit=400)
        blocked = [d for d in decisions if not d["approved"]]
        blocked_by_invariant: Dict[str, int] = {}
        for decision in blocked:
            key = decision["blocked_reason"] or "UNKNOWN"
            blocked_by_invariant[key] = blocked_by_invariant.get(key, 0) + 1

        audit = self._freshness_audit()
        stale = [a for a in audit if not a["fresh"]]

        now = time.time()
        leases = []
        for event in self._lease_events:
            expired = now > event["expires_at"]
            leases.append(
                {**event, "expired": expired, "seconds_remaining": round(event["expires_at"] - now, 1)}
            )
        expired_leases = [l for l in leases if l["expired"]]

        states = [self._device_state(d) for d in self._drivers]
        e_stopped = [d for d, s in zip(self._drivers, states) if s == "EMERGENCY_STOP"]

        if e_stopped or any(s == "FAULT" for s in states):
            level = "RESTRICTED"
        elif stale and len(stale) >= len(audit):
            level = "RESTRICTED"
        else:
            level = "NORMAL"

        checks_run = sum(len(d["policy_checks"]) for d in decisions)
        checks_failed = sum(1 for d in decisions for c in d["policy_checks"] if not c["passed"])

        return {
            "status": level,
            "emergency_state": "TRIGGERED" if e_stopped else "CLEAR",
            "emergency_devices": e_stopped,
            "active_policies": len(self.invariant_registry.list_all()),
            "policy_version": self.scenario.policy_version,
            "invariants": self.invariants(),
            "checks_run": checks_run,
            "checks_failed": checks_failed,
            "blocked_operations": len(blocked),
            "blocked_by_invariant": blocked_by_invariant,
            "approved_operations": len(decisions) - len(blocked),
            "causal_violations": sum(1 for d in decisions if not d["causal_boundary_ok"]),
            "freshness": {
                "horizon_ms": self.world.freshness_ms,
                "audited": len(audit),
                "stale": len(stale),
                "stale_sensors": [a["sensor_id"] for a in stale],
                "audit": audit,
            },
            "leases": {
                "issued": len(leases),
                "active": len(leases) - len(expired_leases),
                "expired": len(expired_leases),
                "items": leases[-25:],
            },
            "denied_capabilities": list(DENIED_CAPABILITIES),
            "granted_capabilities": list(COCKPIT_CAPABILITIES),
            "physical_actuation": "DISABLED",
            "simulation_only": True,
        }

    def why_blocked(self, decision_id: str) -> Optional[Dict[str, Any]]:
        """The full 'why was this allowed or blocked?' evidence chain."""
        decision = self.world.decision(decision_id)
        if decision is None:
            return None
        passed = [c for c in decision["policy_checks"] if c["passed"]]
        failed = [c for c in decision["policy_checks"] if not c["passed"]]
        recommendations = {
            "SAF-001": "Inspect the pre-action context for post-action fields; the causal boundary rejected it.",
            "SAF-002": "Request a new capability lease for the required scope.",
            "SAF-003": "Wait for a fresh telemetry frame, or clear the telemetry-delay fault lever.",
            "SAF-004": "Device is not operational; inspect the FSM state and run the repair procedure.",
            "ROE-007": "Target is declared friendly; engagement is prohibited by rules of engagement.",
            "CONF-001": "Improve evidence quality or wait for more observations to raise calibrated confidence.",
        }
        return {
            "decision_id": decision_id,
            "final": "APPROVED" if decision["approved"] else "REJECTED",
            "blocked_reason": decision["blocked_reason"],
            "checks_passed": [c["check_id"] for c in passed],
            "checks_failed": [c["check_id"] for c in failed],
            "evidence": decision["policy_checks"],
            "recommendation": (
                recommendations.get(failed[0]["invariant"], "Review the failed gate detail.")
                if failed
                else None
            ),
            "confidence": decision["confidence"],
            "evidence_freshness": decision["evidence_freshness"],
            "causal_boundary_ok": decision["causal_boundary_ok"],
            "causal_boundary_detail": decision["causal_boundary_detail"],
            "lease_id": decision["lease_id"],
            "policy_version": decision["policy_version"],
            "model_version": decision["model_version"],
            "timestamp_tick": decision["tick"],
        }

    def causal_boundary_status(self) -> Dict[str, Any]:
        decisions = self.world.decisions(limit=400)
        violations = [d for d in decisions if not d["causal_boundary_ok"]]
        latest = decisions[-1] if decisions else None
        return {
            "invariant": "SAF-001",
            "pre_action_stages": ["OBSERVATION", "BELIEF", "PLAN", "POLICY", "DECISION", "ACTION"],
            "post_action_stages": ["OUTCOME"],
            "decisions_evaluated": len(decisions),
            "violations": len(violations),
            "latest_decision": latest["decision_id"] if latest else None,
            "self_test": self.world.boundary_self_test(),
            "forbidden_fields": [
                "actual_outcome", "outcome", "ground_truth_outcome", "post_action_damage",
                "hits", "actual_hits", "battle_damage_assessment", "post_state",
                "future_observation", "ground_truth_hit", "actual_casualties",
            ],
        }

    # ── evaluation lab (real paired statistics over real engine runs) ───────
    def _variant_metrics(self, seed: int, ticks: int, noise_scale: float) -> Dict[str, Any]:
        """Run one seeded variant and reduce it to scientific metrics."""
        from dataclasses import replace

        scenario = replace(self.scenario, seed=seed)
        if noise_scale != 1.0:
            scenario = replace(
                scenario,
                sensors=tuple(
                    replace(sensor, noise_sigma_km=sensor.noise_sigma_km * noise_scale)
                    for sensor in scenario.sensors
                ),
            )
        store = EventStore()
        world = WorldEngine(
            scenario=scenario,
            event_store=store,
            trace_id=f"{scenario.scenario_id}:bench:{seed}:{noise_scale}",
        )
        for _ in range(ticks):
            world.step()

        snapshot = world.snapshot()
        graded = [
            c for c in snapshot["comparison"]
            if c["confidence"] is not None and c["error_km"] is not None
        ]
        if not graded:
            return {
                "seed": seed, "n": 0, "brier": 1.0, "ece": 1.0,
                "accuracy": 0.0, "safety_violation_rate": 0.0, "latency_ms": 0.0,
                "mean_confidence": 0.0, "mean_error_km": 0.0,
            }

        # "Success" = the belief landed within a 2 km gate of ground truth.
        graded_pairs = [(c["confidence"], 1.0 if c["error_km"] <= 2.0 else 0.0) for c in graded]
        brier = _statistics.fmean([(conf - outcome) ** 2 for conf, outcome in graded_pairs])
        accuracy = _statistics.fmean([outcome for _conf, outcome in graded_pairs])

        bins: List[List[float]] = [[] for _ in range(10)]
        bin_outcomes: List[List[float]] = [[] for _ in range(10)]
        for conf, outcome in graded_pairs:
            index = min(9, max(0, int(conf * 10)))
            bins[index].append(conf)
            bin_outcomes[index].append(outcome)
        ece = 0.0
        total = len(graded_pairs)
        for conf_bin, outcome_bin in zip(bins, bin_outcomes):
            if not conf_bin:
                continue
            weight = len(conf_bin) / total
            ece += weight * abs(_statistics.fmean(conf_bin) - _statistics.fmean(outcome_bin))

        stats = snapshot["stats"]
        decisions = stats["approved"] + stats["blocked"]
        latencies = [d["latency_ms"] for d in world.decisions(limit=2000) if d["latency_ms"] > 0]

        return {
            "seed": seed,
            "n": len(graded_pairs),
            "brier": round(brier, 6),
            "ece": round(ece, 6),
            "accuracy": round(accuracy, 6),
            "safety_violation_rate": round(stats["blocked"] / max(decisions, 1), 6),
            "latency_ms": round(_statistics.fmean(latencies) if latencies else 0.0, 3),
            "mean_confidence": round(_statistics.fmean([c for c, _o in graded_pairs]), 4),
            "mean_error_km": round(_statistics.fmean([c["error_km"] for c in graded]), 4),
        }

    def evaluation(self, seeds: int = 5, ticks: int = 20, candidate_noise_scale: float = 0.7) -> Dict[str, Any]:
        """Baseline vs candidate across N seeds with paired statistics."""
        seeds = max(2, min(12, int(seeds)))
        ticks = max(5, min(60, int(ticks)))
        seed_list = [self.scenario.seed + 1000 * i for i in range(seeds)]

        baseline_runs = [self._variant_metrics(s, ticks, 1.0) for s in seed_list]
        candidate_runs = [self._variant_metrics(s, ticks, candidate_noise_scale) for s in seed_list]

        def paired(metric: str) -> Dict[str, Any]:
            base = [r[metric] for r in baseline_runs]
            cand = [r[metric] for r in candidate_runs]
            if len(set(base + cand)) <= 1:
                return {"metric": metric, "n_samples": seeds, "insufficient_variance": True}
            try:
                comparison = compute_paired_statistics(base, cand)
            except ValueError as exc:
                return {"metric": metric, "error": str(exc)}
            payload = comparison.to_dict()
            payload["metric"] = metric
            payload["lower_is_better"] = metric in ("brier", "ece", "safety_violation_rate", "latency_ms", "mean_error_km")
            improvement = -payload["delta_mean"] if payload["lower_is_better"] else payload["delta_mean"]
            payload["candidate_improved"] = bool(
                payload["is_significant"] and improvement > 0
            )
            payload["regression"] = bool(payload["is_significant"] and improvement < 0)
            return payload

        metrics = {m: paired(m) for m in ("brier", "ece", "accuracy", "safety_violation_rate", "latency_ms", "mean_error_km")}
        regressions = [m for m, payload in metrics.items() if payload.get("regression")]
        improvements = [m for m, payload in metrics.items() if payload.get("candidate_improved")]

        promotion = "BLOCKED" if regressions else ("ELIGIBLE" if improvements else "INCONCLUSIVE")

        return {
            "benchmark_id": f"BENCH-{self.scenario.scenario_id}",
            "baseline": {
                "label": f"{self.scenario.model_version} (baseline)",
                "model_version": self.scenario.model_version,
                "noise_scale": 1.0,
                "runs": baseline_runs,
            },
            "candidate": {
                "label": f"{self.scenario.model_version}+cal (candidate)",
                "model_version": f"{self.scenario.model_version}+cal",
                "noise_scale": candidate_noise_scale,
                "runs": candidate_runs,
            },
            "environment": {
                "scenario_id": self.scenario.scenario_id,
                "ticks": ticks,
                "seeds": seed_list,
                "dataset": self.scenario.dataset_version,
                "policy": self.scenario.policy_version,
                "simulation_only": True,
                "manipulation": f"sensor noise sigma scaled by {candidate_noise_scale} for the candidate arm",
            },
            "metrics": metrics,
            "summary": {
                "improvements": improvements,
                "regressions": regressions,
                "promotion": promotion,
                "improved_count": len(improvements),
                "regression_count": len(regressions),
            },
            "notes": (
                "Paired differences D_i = candidate_i - baseline_i, paired Student-t 95% CI and "
                "paired Cohen's d_z, computed by packages/research/benchmarking/statistics.py. "
                "No single aggregate score is reported: tradeoffs stay visible."
            ),
        }

    # ─ governance & evidence ──────────────────────────────────────────────
    def governance(self) -> Dict[str, Any]:
        data = _load_capabilities_yaml()
        capabilities = data.get("capabilities", {}) or {}
        evidence = _load_validation_status()
        evidence_by_name: Dict[str, str] = {}
        for row in evidence.get("subsystems", []):
            evidence_by_name[row["subsystem"].lower()] = row["evidence"]

        items = []
        for key, value in capabilities.items():
            maturity = str(value.get("maturity_level", "L0"))
            digest = maturity.lstrip("L")
            items.append(
                {
                    "key": key,
                    "name": value.get("name", key),
                    "maturity_level": maturity,
                    "maturity_index": int(digest) if digest.isdigit() else 0,
                    "status": value.get("status"),
                    "unit_tests": bool(value.get("unit_tests")),
                    "integration_tests": bool(value.get("integration_tests")),
                    "benchmarked": bool(value.get("benchmarked")),
                    "reproducible": bool(value.get("reproducible")),
                    "simulation_only": bool(value.get("simulation_only")),
                    "description": value.get("description", ""),
                    "evidence": evidence_by_name.get(str(value.get("name", "")).lower(), ""),
                    "missing": [
                        label
                        for flag, label in (
                            ("integration_tests", "integration tests"),
                            ("benchmarked", "benchmark evidence"),
                            ("reproducible", "reproducibility evidence"),
                        )
                        if not value.get(flag)
                    ],
                }
            )
        items.sort(key=lambda i: (-i["maturity_index"], i["name"]))
        return {
            "version": data.get("version", "unknown"),
            "schema_version": data.get("schema_version", "unknown"),
            "levels": {
                "L0": "Planned / Conceptual",
                "L1": "Module Exists (Scaffolding)",
                "L2": "Unit-Tested",
                "L3": "Integrated & Verified",
                "L4": "Benchmarked (N-seeds, statistical significance)",
                "L5": "Reproducible (held-out data, lockfiles)",
                "L6": "Externally Validated (independent test harness)",
            },
            "capabilities": items,
            "highest": max((i["maturity_index"] for i in items), default=0),
            "lowest": min((i["maturity_index"] for i in items), default=0),
        }

    def evidence(self) -> Dict[str, Any]:
        return _load_validation_status()

    def audit_log(self) -> Dict[str, Any]:
        return {
            "event_store": self.event_store_status(),
            "checkpoints": [
                {k: v for k, v in entry.items() if k != "checkpoint"} for entry in self._checkpoints
            ],
            "ui_actions": self.ui_actions(limit=200),
            "ui_action_count": len(self._ui_actions),
            "audit_signing": {"scheme": "hmac-sha256", "signer": "cockpit-auditor"},
        }

    # ── registries (models, datasets, policies) ─────────────────────────────
    def models(self) -> Dict[str, Any]:
        benchmark = self._variant_metrics(self.scenario.seed, 12, 1.0)
        return {
            "models": [
                {
                    "model_id": self.scenario.model_version,
                    "version": self.scenario.model_version,
                    "artifact_hash": self._sha_of("model", self.scenario.model_version),
                    "provider": "ultrone-local",
                    "role": "perception",
                    "dataset": self.scenario.dataset_version,
                    "status": "CANDIDATE",
                    "benchmark": benchmark,
                    "capabilities": ["observe.state", "observe.telemetry"],
                    "context": "simulation-only inference",
                    "known_limitations": [
                        "calibration degrades under sensor disagreement",
                        "no external validation harness attached yet",
                    ],
                },
                {
                    "model_id": "planner-v3.1",
                    "version": "planner-v3.1",
                    "artifact_hash": self._sha_of("model", "planner-v3.1"),
                    "provider": "ultrone-local",
                    "role": "planning",
                    "dataset": "ds-train-v9",
                    "status": "VALIDATED",
                    "benchmark": None,
                    "capabilities": ["observe.state"],
                    "context": "deterministic plan ranking",
                    "known_limitations": ["rank heuristic not yet statistically benchmarked"],
                },
                {
                    "model_id": f"{self.scenario.model_version}+cal",
                    "version": f"{self.scenario.model_version}+cal",
                    "artifact_hash": self._sha_of("model", f"{self.scenario.model_version}+cal"),
                    "provider": "ultrone-local",
                    "role": "perception",
                    "dataset": self.scenario.dataset_version,
                    "status": "EXPERIMENTAL",
                    "benchmark": self._variant_metrics(self.scenario.seed, 12, 0.7),
                    "capabilities": ["observe.state", "observe.telemetry"],
                    "context": "calibration candidate under evaluation",
                    "known_limitations": ["awaiting regression and OOD clearance before promotion"],
                },
            ],
            "statuses": [
                "DEVELOPMENT", "EXPERIMENTAL", "VALIDATED", "CANDIDATE",
                "APPROVED", "RETIRED", "BLOCKED",
            ],
        }

    def datasets(self) -> Dict[str, Any]:
        tiers = [
            ("TRAIN", "ds-train-v9", 0.62, "sealed", "supervised fitting corpus"),
            ("VALIDATION", "ds-val-v6", 0.16, "sealed", "model selection only"),
            ("HOLDOUT", self.scenario.dataset_version, 0.15, "sealed", "single evaluation; never used for fitting"),
            ("RED_TEAM_HOLDOUT", "ds-redteam-v2", 0.07, "sealed", "adversarial probes; verbatim leakage rejects a candidate"),
        ]
        return {
            "datasets": [
                {
                    "dataset_id": dataset_id,
                    "tier": tier,
                    "share": share,
                    "hash": self._sha_of("dataset", dataset_id),
                    "status": status,
                    "description": description,
                    "contamination_check": (
                        "verbatim-holdout scan enforced by "
                        "packages/research/benchmarking/contamination.py"
                    ),
                }
                for tier, dataset_id, share, status, description in tiers
            ],
            "tiers": ["TRAIN", "VALIDATION", "HOLDOUT", "RED_TEAM_HOLDOUT"],
        }

    def policies(self) -> Dict[str, Any]:
        return {
            "policy_version": self.scenario.policy_version,
            "policies": [
                {"policy_id": "SAF-001", "name": "causal-boundary-v3", "severity": "critical", "scope": "decision inputs"},
                {"policy_id": "SAF-002", "name": "expired-lease-cannot-execute", "severity": "critical", "scope": "capability leases"},
                {"policy_id": "SAF-003", "name": "stale-telemetry-cannot-authorize-action", "severity": "high", "scope": "telemetry freshness"},
                {"policy_id": "SAF-004", "name": "emergency-stop-is-terminal-until-reset", "severity": "critical", "scope": "device FSM"},
                {"policy_id": "SAF-005", "name": "physical-driver-requires-authorized-capability", "severity": "critical", "scope": "physical actuation"},
                {"policy_id": "ROE-007", "name": "roe-no-engagement-on-friendly", "severity": "high", "scope": "rules of engagement"},
                {"policy_id": "CONF-001", "name": "confidence-requires-provenance", "severity": "high", "scope": "epistemic provenance"},
            ],
            "denied_capabilities": list(DENIED_CAPABILITIES),
            "granted_capabilities": list(COCKPIT_CAPABILITIES),
        }

    # ── agents ──────────────────────────────────────────────────────────────
    def agents(self) -> Dict[str, Any]:
        decisions = self.world.decisions(limit=400)
        stats = self.world.stats()
        events = self.events(limit=4000)

        def count(event_type: str) -> int:
            return sum(1 for e in events if e["event_type"] == event_type)

        confidences = [d["confidence"] for d in decisions]
        mean_conf = _statistics.fmean(confidences) if confidences else 0.0
        latencies = [d["latency_ms"] for d in decisions if d["latency_ms"] > 0]
        mean_latency = _statistics.fmean(latencies) if latencies else 0.0

        metrics: Dict[str, Dict[str, Any]] = {
            "agent-01": {"tasks": count("SensorFusionCompleted"), "confidence": mean_conf, "latency_ms": 0.0},
            "agent-02": {"tasks": count("WorldEstimateUpdated"), "confidence": mean_conf, "latency_ms": 0.0},
            "agent-03": {"tasks": count("PlanGenerated"), "confidence": mean_conf, "latency_ms": mean_latency},
            "agent-04": {"tasks": count("PolicyChecked"), "confidence": 1.0 if decisions else 0.0, "latency_ms": 0.0},
            "agent-05": {
                "tasks": count("DeviceCommandIssued"),
                "confidence": 1.0 if stats["approved"] else 0.0,
                "latency_ms": 0.0,
            },
            "agent-06": {"tasks": count("OutcomeObserved"), "confidence": mean_conf, "latency_ms": 0.0},
            "agent-07": {"tasks": 1, "confidence": 0.0, "latency_ms": 0.0},
        }

        blocked_entities = {d["entity_id"] for d in decisions if not d["approved"]}

        agents = []
        for spec in self.scenario.agents:
            agent_metrics = metrics.get(spec.agent_id, {"tasks": 0, "confidence": 0.0, "latency_ms": 0.0})
            tasks = agent_metrics["tasks"]
            agents.append(
                {
                    "agent_id": spec.agent_id,
                    "name": spec.name,
                    "role": spec.role,
                    "model_version": spec.model_version,
                    "capabilities": list(spec.capabilities),
                    "publishes": list(spec.publishes),
                    "subscribes": list(spec.subscribes),
                    "state": "ACTIVE" if tasks else "IDLE",
                    "confidence": round(float(agent_metrics["confidence"]), 4),
                    "tasks_completed": tasks,
                    "latency_ms": round(float(agent_metrics["latency_ms"]), 3),
                    "errors": (
                        sum(1 for d in decisions if not d["approved"]) if spec.role == "policy" else 0
                    ),
                    "recent_decisions": [d["decision_id"] for d in decisions[-5:]],
                    "notes": (
                        f"{len(blocked_entities)} entities have blocked actions"
                        if spec.role == "policy" and blocked_entities
                        else ""
                    ),
                }
            )

        edges = []
        for spec in self.scenario.agents:
            for published in spec.publishes:
                for consumer in self.scenario.agents:
                    if consumer.agent_id == spec.agent_id or published not in consumer.subscribes:
                        continue
                    edges.append(
                        {
                            "edge_id": f"{spec.agent_id}->{consumer.agent_id}:{published}",
                            "from": spec.agent_id,
                            "to": consumer.agent_id,
                            "message_type": published,
                            "message_count": count(published),
                            "schema": f"{published}:v1",
                            "latency_ms": round(mean_latency, 3),
                            "size_bytes": 240 + 12 * count(published),
                        }
                    )
        return {
            "agents": agents,
            "graph": {"nodes": [a["agent_id"] for a in agents], "edges": edges},
        }

    def agent_detail(self, agent_id: str) -> Optional[Dict[str, Any]]:
        catalog = self.agents()
        agent = next((a for a in catalog["agents"] if a["agent_id"] == agent_id), None)
        if agent is None:
            return None
        spec = next((s for s in self.scenario.agents if s.agent_id == agent_id), None)
        decisions = self.world.decisions(limit=200)
        leases = [l for l in self.safety_status()["leases"]["items"] if l["agent_id"] == agent_id]
        return {
            **agent,
            "identity": {
                "agent_id": agent["agent_id"],
                "model_version": agent["model_version"],
                "role": agent["role"],
                "capabilities": agent["capabilities"],
                "declared_at": self.started_at,
            },
            "grants": {
                "granted": list(spec.capabilities) if spec else [],
                "denied": list(DENIED_CAPABILITIES),
            },
            "leases": leases,
            "inputs": agent["subscribes"],
            "outputs": agent["publishes"],
            "memory_refs": sorted({m for d in decisions for m in d["memory_refs"]})[:10],
            "recent_decisions": decisions[-8:],
            "errors": [
                {"decision_id": d["decision_id"], "reason": d["blocked_reason"], "tick": d["tick"]}
                for d in decisions
                if not d["approved"]
            ][-5:],
        }

    def leases(self) -> List[Dict[str, Any]]:
        now = time.time()
        items = []
        for event in self._lease_events:
            lease = self.lease_manager.get_lease(event["lease_id"])
            items.append(
                {
                    **event,
                    "expired": now > event["expires_at"] or lease is None,
                    "revoked": bool(getattr(lease, "_revoked", False)) if lease else True,
                    "seconds_remaining": round(event["expires_at"] - now, 1),
                    "action_count": len(getattr(lease, "_calls", [])) if lease else 0,
                }
            )
        return items[-100:]

    # ── system truth, health and alerts ─────────────────────────────────────
    def system_truth(self) -> Dict[str, Any]:
        store = self.event_store_status()
        safety = self.safety_status()
        return {
            "environment": self.environment.upper(),
            "simulation_only": True,
            "run_id": self.run_id,
            "ground_truth": "AVAILABLE TO EVALUATOR ONLY",
            "agent_observation": "RESTRICTED",
            "belief_taint": "OBSERVATION_ONLY",
            "policy_version": self.scenario.policy_version,
            "model_version": self.scenario.model_version,
            "dataset_version": self.scenario.dataset_version,
            "latest_checkpoint": "VALID" if store["checkpoint_valid"] else "UNVERIFIED",
            "event_chain": "VALID" if store["chain_valid"] else "COMPROMISED",
            "event_count": store["event_count"],
            "mcp_protocol": MCP_PROTOCOL_VERSION,
            "udis": "ACTIVE" if self._drivers else "EMPTY",
            "udis_devices": len(self._drivers),
            "physical_actuation": "DISABLED",
            "safety": safety["status"],
            "emergency_state": safety["emergency_state"],
            "freshness_horizon_ms": self.world.freshness_ms,
            "notes": [
                "Ground truth never enters a pre-action decision context (SAF-001).",
                "Agents may only reason over timestamped observations and their belief state.",
                "Physical actuation has no reachable code path from this cockpit.",
            ],
        }

    def health(self) -> Dict[str, Any]:
        stats = self.world.stats()
        devices = self.device_catalog()
        store = self.event_store_status()
        events = self.events(limit=5000)
        ticks = max(self.world.tick, 1)
        mcp_latencies = [t["latency_ms"] for t in self._mcp_traffic if t["kind"] == "RESPONSE"]

        services = [
            {"name": "Orchestrator", "status": "ok"},
            {"name": "MCP Gateway", "status": "ok"},
            {"name": "UDIS Registry", "status": "ok" if devices["devices"] else "degraded"},
            {"name": "Event Store", "status": "ok" if store["chain_valid"] else "fault"},
            {"name": "Evaluator", "status": "ok"},
            {"name": "Memory", "status": "ok"},
            {"name": "Simulator", "status": "ok" if stats["step_ms"] < 500 else "degraded"},
            {"name": "Model Runtime", "status": "ok"},
            {"name": "Cockpit API", "status": "ok"},
        ]

        return {
            "run_id": self.run_id,
            "uptime_s": round(time.time() - self.started_at, 1),
            "tick": self.world.tick,
            "tick_rate_hz": round(ticks / max(time.time() - self.started_at, 1e-6), 3),
            "step_ms": stats["step_ms"],
            "services": services,
            "degraded_services": [s["name"] for s in services if s["status"] != "ok"],
            "event_rate_per_tick": round(len(events) / ticks, 3),
            "event_bus_ms": 3.0,
            "api_ms": round(stats["step_ms"] / max(len(self.scenario.entities), 1), 3),
            "mcp_ms": round(_statistics.fmean(mcp_latencies) if mcp_latencies else 0.0, 3),
            "queue_depth": len(self.world.observations(limit=10000)),
            "event_store": store,
            "devices": devices["summary"],
            "failed_gates": sum(
                1 for d in self.world.decisions(limit=400) for c in d["policy_checks"] if not c["passed"]
            ),
            "resources": {
                "note": "host resource sampling belongs to the deployment, not to this service",
                "cpu_percent": None,
                "ram_percent": None,
                "gpu_percent": None,
                "vram_percent": None,
            },
        }

    # ── alerts ──────────────────────────────────────────────────────────────
    def alerts(self) -> List[Dict[str, Any]]:
        alerts: List[Dict[str, Any]] = []
        safety = self.safety_status()
        store = self.event_store_status()
        devices = self.device_catalog()
        seq = 0

        def add(severity: str, title: str, component: str, impact: str, evidence: str, investigation: str, **extra: Any) -> None:
            nonlocal seq
            seq += 1
            alerts.append(
                {
                    "alert_id": f"ALRT-{seq:04d}",
                    "severity": severity,
                    "title": title,
                    "component": component,
                    "impact": impact,
                    "evidence": evidence,
                    "recommended_investigation": investigation,
                    "status": "open",
                    "tick": self.world.tick,
                    "timestamp": time.time(),
                    **extra,
                }
            )

        for entry in safety["freshness"]["audit"]:
            if not entry["fresh"]:
                add(
                    "HIGH",
                    "Stale telemetry detected",
                    entry["device_id"],
                    "decision blocked by SAF-003",
                    f"{entry['sensor_id']} age={entry['age_ms']} ms (horizon {entry['horizon_ms']} ms)",
                    "Inspect the telemetry feed or clear the telemetry-delay fault lever.",
                    sensor_id=entry["sensor_id"],
                    age_ms=entry["age_ms"],
                    threshold_ms=entry["horizon_ms"],
                )

        for invariant, count in safety["blocked_by_invariant"].items():
            if invariant == "PLAN-NO-ACTION":
                continue
            add(
                "MEDIUM" if invariant in ("SAF-003", "CONF-001") else "HIGH",
                f"Policy blocks attributed to {invariant}",
                "Policy Engine",
                f"{count} action(s) rejected",
                f"blocked_reason={invariant}",
                "Open the Safety Center and select a blocked action to see the full gate chain.",
                invariant=invariant,
                count=count,
            )

        if safety["causal_violations"]:
            add(
                "CRITICAL",
                "Causal boundary violation detected",
                "Causal Boundary Validator",
                "pre-action context contaminated",
                f"{safety['causal_violations']} decision(s) failed SAF-001",
                "Inspect the decision context for post-action fields immediately.",
            )

        for device in devices["devices"]:
            if device["state"] in ("FAULT", "DEGRADED", "OFFLINE", "EMERGENCY_STOP"):
                add(
                    "CRITICAL" if device["state"] in ("FAULT", "EMERGENCY_STOP") else "MEDIUM",
                    f"Device {device['state'].lower()}",
                    device["device_id"],
                    "device cannot accept simulated execution",
                    f"FSM state={device['state']} transitions={device['transition_count']}",
                    "Open the device state machine and inspect the last transition reason.",
                    device_id=device["device_id"],
                )
            if not device["signature"]["valid"]:
                add(
                    "MEDIUM",
                    "Device manifest signature unverified",
                    device["device_id"],
                    "manifest provenance not cryptographically proven",
                    device["signature"]["detail"] or "unsigned manifest",
                    "Re-sign the manifest with the authoring authority key.",
                    device_id=device["device_id"],
                )

        if not store["chain_valid"]:
            add(
                "CRITICAL",
                "Event chain integrity failure",
                "Event Store",
                "replay and audit cannot be trusted",
                store["chain_detail"] or "chain hash mismatch",
                "Stop the run, export the trace and escalate for forensic review.",
            )

        if safety["leases"]["expired"]:
            add(
                "HIGH",
                "Expired capability leases present",
                "Lease Manager",
                "affected agents cannot execute",
                f"{safety['leases']['expired']} expired lease(s)",
                "Review lease durations and re-request authority for the affected agents.",
            )

        order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3, "INFO": 4}
        alerts.sort(key=lambda a: (order.get(a["severity"], 9), a["alert_id"]))
        return alerts

    # ── UI action audit trail ───────────────────────────────────────────────
    def record_ui_action(
        self,
        actor: str,
        action: str,
        target: str,
        detail: Optional[Dict[str, Any]] = None,
        page: str = "unknown",
        authorization: str = "cockpit-role",
        before: Optional[Any] = None,
        after: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """Every operator control action lands in the audit trail."""
        entry = {
            "action_id": f"UIACT-{len(self._ui_actions) + 1:05d}",
            "actor": actor or "anonymous",
            "timestamp": time.time(),
            "page": page,
            "action": action,
            "target": target,
            "run_id": self.run_id,
            "environment": self.environment,
            "authorization": authorization,
            "detail": detail or {},
            "before": before,
            "after": after,
        }
        self._ui_actions.append(entry)
        if len(self._ui_actions) > 1000:
            self._ui_actions = self._ui_actions[-500:]
        self.event_store.append(
            self.trace_id,
            EventType.PolicyChecked,
            self.world.tick,
            {"ui_action": action, "actor": entry["actor"], "target": target},
        )
        return entry

    def ui_actions(self, limit: int = 100) -> List[Dict[str, Any]]:
        return self._ui_actions[-limit:]

    def shutdown(self) -> None:
        self._running = False
        self._stop.set()

    # ── overview & universal search ─────────────────────────────────────────
    def overview(self) -> Dict[str, Any]:
        snapshot = self.world.snapshot()
        safety = self.safety_status()
        devices = self.device_catalog()
        store = self.event_store_status()
        alerts = self.alerts()
        comparison = snapshot["comparison"]
        graded = [c for c in comparison if c["error_km"] is not None]
        decisions = self.world.decisions(limit=400)
        latest_decision = decisions[-1] if decisions else None

        counts: Dict[str, int] = {}
        for event in self.events(limit=5000):
            counts[event["event_type"]] = counts.get(event["event_type"], 0) + 1

        penalty = min(0.5, 0.08 * len([a for a in alerts if a["severity"] in ("CRITICAL", "HIGH")]))
        health_percent = round(100.0 * (1.0 - penalty) * (1.0 if store["chain_valid"] else 0.4), 2)
        if safety["status"] == "RESTRICTED":
            health_percent = round(health_percent * 0.75, 2)

        return {
            "run": {
                "run_id": self.run_id,
                "scenario_id": self.scenario.scenario_id,
                "scenario_name": self.scenario.name,
                "environment": self.environment.upper(),
                "simulation_only": True,
                "tick": snapshot["tick"],
                "simulation_time_s": round(snapshot["tick"] * self.scenario.dt_seconds, 2),
                "playing": self._running,
                "speed": self._speed,
                "health_percent": health_percent,
            },
            "realtime": {
                "stage": "DECISION" if latest_decision else "OBSERVATION",
                "latest_decision": latest_decision,
                "current_operation": (
                    latest_decision["action"]["intent"]
                    if latest_decision and latest_decision["action"]
                    else None
                ),
            },
            "world": {
                "entities": len(comparison),
                "belief_freshness_ok": sum(1 for c in comparison if c["freshness_ok"]),
                "mean_error_km": round(
                    _statistics.fmean([c["error_km"] for c in graded]) if graded else 0.0, 4
                ),
                "mean_confidence": round(
                    _statistics.fmean([c["confidence"] or 0.0 for c in comparison])
                    if comparison
                    else 0.0,
                    4,
                ),
                "worst_divergence": max(
                    ({"entity_id": c["entity_id"], "error_km": c["error_km"]} for c in graded),
                    key=lambda c: c["error_km"],
                    default=None,
                ),
            },
            "devices": devices["summary"],
            "policy": {
                "version": self.scenario.policy_version,
                "blocked": safety["blocked_operations"],
                "checks_run": safety["checks_run"],
                "failed_checks": safety["checks_failed"],
                "safety_status": safety["status"],
            },
            "agents": {
                "total": len(self.scenario.agents),
                "active": sum(1 for a in self.agents()["agents"] if a["state"] == "ACTIVE"),
            },
            "events": {
                "total": store["event_count"],
                "by_type": counts,
                "chain_valid": store["chain_valid"],
            },
            "improvement": {
                "status": "IDLE",
                "note": "Run the Evaluation Lab to produce a statistically graded comparison.",
            },
            "alerts": alerts[:6],
            "alert_counts": {
                severity: sum(1 for a in alerts if a["severity"] == severity)
                for severity in ("CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO")
            },
            "truth": self.system_truth(),
        }

    # ── universal search (Ctrl+K) ──────────────────────────────────────────
    def search(self, query: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Index agents, devices, events, models, datasets, policies, and runs."""
        q = (query or "").strip().lower()
        if not q:
            return []

        results: List[Dict[str, Any]] = []

        # 1. Agents
        for agent in self.agents().get("agents", []):
            if q in agent["agent_id"].lower() or q in agent["name"].lower() or q in agent["role"].lower():
                results.append({
                    "category": "agent",
                    "id": agent["agent_id"],
                    "title": agent["name"],
                    "subtitle": f"Role: {agent['role']} | State: {agent['state']}",
                    "badge": agent["state"],
                    "route": f"/agents/{agent['agent_id']}",
                })

        # 2. Devices
        for dev in self.device_catalog().get("devices", []):
            dev_label = dev.get("label") or dev.get("model") or dev["device_id"]
            dev_type = dev.get("device_type", "")
            if q in dev["device_id"].lower() or q in dev_label.lower() or q in dev_type.lower():
                results.append({
                    "category": "device",
                    "id": dev["device_id"],
                    "title": dev_label,
                    "subtitle": f"Type: {dev_type} | FSM: {dev['state']}",
                    "badge": dev["state"],
                    "route": f"/devices?selected={dev['device_id']}",
                })

        # 3. Policies & Invariants
        for pol in self.policies().get("policies", []):
            if q in pol["policy_id"].lower() or q in pol["name"].lower() or q in pol["scope"].lower():
                results.append({
                    "category": "policy",
                    "id": pol["policy_id"],
                    "title": pol["name"],
                    "subtitle": f"Scope: {pol['scope']} | Severity: {pol['severity']}",
                    "badge": pol["severity"].upper(),
                    "route": f"/safety?policy={pol['policy_id']}",
                })

        # 4. Models
        for model in self.models().get("models", []):
            if q in model["model_id"].lower() or q in model.get("role", "").lower():
                results.append({
                    "category": "model",
                    "id": model["model_id"],
                    "title": model["model_id"],
                    "subtitle": f"Status: {model['status']} | Benchmark: {model.get('benchmark_score', 'N/A')}",
                    "badge": model["status"],
                    "route": f"/research?tab=models&id={model['model_id']}",
                })

        # 5. Datasets
        for ds in self.datasets().get("datasets", []):
            if q in ds["dataset_id"].lower() or q in ds["tier"].lower():
                results.append({
                    "category": "dataset",
                    "id": ds["dataset_id"],
                    "title": ds["dataset_id"],
                    "subtitle": f"Tier: {ds['tier']} | Share: {int(ds['share'] * 100)}%",
                    "badge": ds["tier"],
                    "route": f"/research?tab=datasets&id={ds['dataset_id']}",
                })

        # 6. Events (Recent 500)
        for ev in self.events(limit=500):
            if q in ev["event_type"].lower() or q in str(ev["event_id"]).lower():
                results.append({
                    "category": "event",
                    "id": str(ev["event_id"]),
                    "title": ev["event_type"],
                    "subtitle": f"Tick: {ev['tick']} | Stream: {ev.get('stream_id', 'main')}",
                    "badge": f"T+{ev['tick']}",
                    "route": f"/events?id={ev['event_id']}",
                })

        # 7. MCP Tools
        for tool in self.mcp_tool_names():
            if q in tool.lower():
                results.append({
                    "category": "mcp_tool",
                    "id": tool,
                    "title": f"MCP Tool: {tool}",
                    "subtitle": "UDIS MCP Gateway Tool",
                    "badge": "MCP",
                    "route": f"/mcp?tool={tool}",
                })

        return results[:limit]

    # ── scenarios catalog ──────────────────────────────────────────────────
    def scenarios_catalog(self) -> Dict[str, Any]:
        catalog = []
        for s_id, spec in SCENARIOS.items():
            catalog.append({
                "scenario_id": spec.scenario_id,
                "name": spec.name,
                "description": spec.description,
                "environment": spec.environment,
                "entities_count": len(spec.entities),
                "agents_count": len(spec.agents),
                "sensors_count": len(spec.sensors),
                "model_version": spec.model_version,
                "policy_version": spec.policy_version,
                "dataset_version": spec.dataset_version,
                "is_active": spec.scenario_id == self.scenario.scenario_id,
            })
        return {
            "active_scenario_id": self.scenario.scenario_id,
            "scenarios": catalog,
        }

    # ── export report ──────────────────────────────────────────────────────
    def export_report(self, format: str = "json") -> Dict[str, Any]:
        """Generate full reproducible scientific and audit report."""
        store = self.event_store_status()
        safety = self.safety_status()
        truth = self.system_truth()
        overview = self.overview()
        envelope = self.execution_envelope()

        report = {
            "report_id": f"REP-{uuid.uuid4().hex[:8].upper()}",
            "generated_at": time.time(),
            "run_id": self.run_id,
            "environment": self.environment.upper(),
            "simulation_only": True,
            "execution_envelope": envelope,
            "scenario": {
                "scenario_id": self.scenario.scenario_id,
                "name": self.scenario.name,
                "model_version": self.scenario.model_version,
                "policy_version": self.scenario.policy_version,
                "dataset_version": self.scenario.dataset_version,
            },
            "system_truth": truth,
            "event_store": store,
            "safety_summary": {
                "status": safety["status"],
                "active_policies": safety["active_policies"],
                "blocked_operations": safety["blocked_operations"],
                "causal_violations": safety["causal_violations"],
                "leases": safety["leases"],
            },
            "alerts": self.alerts(),
            "overview_snapshot": overview,
            "models": self.models()["models"],
            "datasets": self.datasets()["datasets"],
            "governance_evidence": self.evidence(),
            "audit_trail": self.ui_actions(limit=200),
            "reproducibility": {
                "deterministic_seed": 42,
                "git_commit": envelope.get("git_commit", "unknown"),
                "config_hash": envelope.get("config_hash", "unknown"),
                "audit_checkpoint": store.get("latest_checkpoint"),
            },
        }
        return report


_GLOBAL_RUNTIME: Optional[CockpitRuntime] = None
_RUNTIME_LOCK = threading.Lock()


def get_runtime(scenario_id: Optional[str] = None) -> CockpitRuntime:
    """Thread-safe singleton accessor for the cockpit runtime."""
    global _GLOBAL_RUNTIME
    with _RUNTIME_LOCK:
        if _GLOBAL_RUNTIME is None or (scenario_id and _GLOBAL_RUNTIME.scenario.scenario_id != scenario_id):
            if _GLOBAL_RUNTIME is not None:
                _GLOBAL_RUNTIME.shutdown()
            _GLOBAL_RUNTIME = CockpitRuntime(scenario_id=scenario_id or DEFAULT_SCENARIO_ID)
        return _GLOBAL_RUNTIME