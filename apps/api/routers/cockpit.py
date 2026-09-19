# Copyright (c) Ultrone Contributors. All rights reserved.
"""FastAPI router for the ULTRONE Autonomy Research & Simulation Cockpit.

Binds the genuine second-generation runtime (UDIS, MCP 2026-07-28, causal boundary,
event sourcing, evaluation, and evidence-backed governance) to the frontend.
"""

from __future__ import annotations

import asyncio
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field

from apps.api.cockpit import get_runtime
from apps.api.cockpit.runtime import CockpitRuntime

router = APIRouter(prefix="/api/cockpit", tags=["cockpit"])


# ── Request Models ───────────────────────────────────────────────────────────

class PlayControlRequest(BaseModel):
    speed: Optional[float] = None
    actor: str = "operator"


class StepControlRequest(BaseModel):
    count: int = Field(default=1, ge=1, le=100)
    actor: str = "operator"


class SpeedControlRequest(BaseModel):
    speed: float = Field(default=1.0, gt=0.0, le=50.0)
    actor: str = "operator"


class FaultInjectionRequest(BaseModel):
    config: Dict[str, Any]
    actor: str = "researcher"


class DeviceTransitionRequest(BaseModel):
    target_state: str
    reason: str = "operator transition request"
    actor: str = "operator"


class DeviceProcedureRequest(BaseModel):
    procedure_name: str
    parameters: Dict[str, Any] = Field(default_factory=dict)
    actor: str = "operator"


class McpToolCallRequest(BaseModel):
    tool: str
    arguments: Dict[str, Any] = Field(default_factory=dict)


class ReplayRequest(BaseModel):
    ticks: Optional[int] = None
    actor: str = "researcher"


class ScenarioSelectRequest(BaseModel):
    scenario_id: str
    actor: str = "researcher"


class UiActionRequest(BaseModel):
    actor: str = "operator"
    action: str
    target: str
    page: str = "cockpit"
    detail: Optional[Dict[str, Any]] = None
    before: Optional[Any] = None
    after: Optional[Any] = None


# ── Global Status, Overview, and Truth ───────────────────────────────────────

@router.get("/status")
def get_status() -> Dict[str, Any]:
    rt = get_runtime()
    overview = rt.overview()
    truth = rt.system_truth()
    return {
        "run": overview["run"],
        "truth": truth,
        "mcp_protocol": "2026-07-28",
        "udis_devices": len(rt._drivers),
        "safety_status": overview["policy"]["safety_status"],
    }


@router.get("/overview")
def get_overview() -> Dict[str, Any]:
    return get_runtime().overview()


@router.get("/truth")
def get_system_truth() -> Dict[str, Any]:
    return get_runtime().system_truth()


@router.get("/health")
def get_health() -> Dict[str, Any]:
    return get_runtime().health()


@router.get("/alerts")
def get_alerts() -> List[Dict[str, Any]]:
    return get_runtime().alerts()


# ── Simulation & Dual World ──────────────────────────────────────────────────

@router.get("/world")
def get_world_snapshot() -> Dict[str, Any]:
    return get_runtime().world.snapshot()


@router.post("/control/play")
def play_simulation(req: PlayControlRequest) -> Dict[str, Any]:
    rt = get_runtime()
    rt.record_ui_action(req.actor, "PLAY", "simulation", page="world")
    return rt.play(speed=req.speed, actor=req.actor)


@router.post("/control/pause")
def pause_simulation(req: PlayControlRequest) -> Dict[str, Any]:
    rt = get_runtime()
    rt.record_ui_action(req.actor, "PAUSE", "simulation", page="world")
    return rt.pause(actor=req.actor)


@router.post("/control/step")
def step_simulation(req: StepControlRequest) -> Dict[str, Any]:
    rt = get_runtime()
    rt.record_ui_action(req.actor, "STEP", f"simulation_count_{req.count}", page="world")
    return rt.step(count=req.count, actor=req.actor)


@router.post("/control/reset")
def reset_simulation(req: PlayControlRequest) -> Dict[str, Any]:
    rt = get_runtime()
    rt.record_ui_action(req.actor, "RESET", "simulation", page="world")
    return rt.reset(actor=req.actor)


@router.post("/control/speed")
def set_speed(req: SpeedControlRequest) -> Dict[str, Any]:
    rt = get_runtime()
    rt.record_ui_action(req.actor, "SET_SPEED", str(req.speed), page="world")
    return rt.set_speed(speed=req.speed, actor=req.actor)


@router.post("/control/faults")
def inject_faults(req: FaultInjectionRequest) -> Dict[str, Any]:
    rt = get_runtime()
    rt.record_ui_action(req.actor, "INJECT_FAULTS", "system", detail=req.config, page="safety")
    return rt.inject_faults(config=req.config, actor=req.actor)


@router.post("/control/clear-faults")
def clear_faults(req: PlayControlRequest) -> Dict[str, Any]:
    rt = get_runtime()
    rt.record_ui_action(req.actor, "CLEAR_FAULTS", "system", page="safety")
    return rt.clear_faults(actor=req.actor)


# ── Intelligence & Agents ───────────────────────────────────────────────────

@router.get("/agents")
def get_agents() -> Dict[str, Any]:
    return get_runtime().agents()


@router.get("/agents/{agent_id}")
def get_agent_detail(agent_id: str) -> Dict[str, Any]:
    detail = get_runtime().agent_detail(agent_id)
    if detail is None:
        raise HTTPException(status_code=404, detail=f"Agent '{agent_id}' not found")
    return detail


# ── Devices & UDIS 10-State FSM ──────────────────────────────────────────────

@router.get("/devices")
def get_devices() -> Dict[str, Any]:
    return get_runtime().device_catalog()


@router.get("/devices/{device_id}")
def get_device_detail(device_id: str) -> Dict[str, Any]:
    detail = get_runtime().device_detail(device_id)
    if detail is None:
        raise HTTPException(status_code=404, detail=f"Device '{device_id}' not found")
    return detail


@router.post("/devices/{device_id}/transition")
def transition_device(device_id: str, req: DeviceTransitionRequest) -> Dict[str, Any]:
    rt = get_runtime()
    driver = rt._drivers.get(device_id)
    if driver is None:
        raise HTTPException(status_code=404, detail=f"Device '{device_id}' not found")

    from packages.runtime.device_protocol.state import DeviceState
    try:
        target = DeviceState(req.target_state.upper())
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid DeviceState '{req.target_state}'")

    current_state = driver.get_state()
    allowed = driver.state_machine.allowed_transitions()
    if target not in allowed:
        raise HTTPException(
            status_code=409,
            detail=f"Illegal transition from {current_state.value} to {target.value}. Allowed: {[s.value for s in allowed]}",
        )

    driver.state_machine.transition_to(target, reason=req.reason)
    rt.record_ui_action(
        req.actor,
        "FSM_TRANSITION",
        device_id,
        page="devices",
        before=current_state.value,
        after=target.value,
    )
    return {
        "device_id": device_id,
        "previous_state": current_state.value,
        "current_state": target.value,
        "allowed_transitions": [s.value for s in driver.state_machine.allowed_transitions()],
    }


@router.post("/devices/{device_id}/procedure")
def execute_device_procedure(device_id: str, req: DeviceProcedureRequest) -> Dict[str, Any]:
    rt = get_runtime()
    manifest = rt._manifests.get(device_id)
    if manifest is None:
        raise HTTPException(status_code=404, detail=f"Device '{device_id}' not found")

    proc = next((p for p in manifest.procedures if p.name == req.procedure_name), None)
    if proc is None:
        raise HTTPException(
            status_code=400,
            detail=f"Procedure '{req.procedure_name}' not in manifest. Available: {[p.name for p in manifest.procedures]}",
        )

    rt.record_ui_action(
        req.actor,
        "EXECUTE_PROCEDURE",
        f"{device_id}:{req.procedure_name}",
        detail=req.parameters,
        page="devices",
    )
    return {
        "status": "completed",
        "device_id": device_id,
        "procedure": req.procedure_name,
        "execution_envelope": rt.execution_envelope(),
        "timestamp": rt.world.tick,
    }


# ── MCP Protocol 2026-07-28 & Traffic DevTools ──────────────────────────────

@router.get("/mcp/traffic")
def get_mcp_traffic(limit: int = 100, method: Optional[str] = None) -> List[Dict[str, Any]]:
    return get_runtime().mcp_traffic(limit=limit, method=method)


@router.get("/mcp/discovery")
def get_mcp_discovery() -> Dict[str, Any]:
    return get_runtime().mcp_discovery()


@router.post("/mcp/tools/call")
def call_mcp_tool(req: McpToolCallRequest) -> Dict[str, Any]:
    return get_runtime().mcp_tool_call(req.tool, req.arguments)


@router.get("/mcp/resources/read")
def read_mcp_resource(uri: str = Query(...)) -> Dict[str, Any]:
    return get_runtime().mcp_resource_read(uri)


# ── Trace, Replay, and Event Store ──────────────────────────────────────────

@router.get("/events")
def get_events(
    limit: int = 200,
    event_type: Optional[str] = None,
    since_tick: Optional[int] = None,
) -> List[Dict[str, Any]]:
    return get_runtime().events(limit=limit, event_type=event_type, since_tick=since_tick)


@router.get("/events/store")
def get_event_store_status() -> Dict[str, Any]:
    return get_runtime().event_store_status()


@router.post("/events/checkpoint")
def create_event_checkpoint(actor: str = "auditor") -> Dict[str, Any]:
    rt = get_runtime()
    rt.record_ui_action(actor, "CREATE_AUDIT_CHECKPOINT", "event_store", page="events")
    return rt.create_checkpoint(actor=actor)


@router.post("/replay")
def run_replay(req: ReplayRequest) -> Dict[str, Any]:
    rt = get_runtime()
    rt.record_ui_action(req.actor, "RUN_REPLAY", f"ticks_{req.ticks or 'all'}", page="replay")
    return rt.replay(ticks=req.ticks, actor=req.actor)


@router.get("/traces")
def get_decision_traces(limit: int = 100) -> List[Dict[str, Any]]:
    return get_runtime().world.decisions(limit=limit)


@router.get("/traces/{decision_id}")
def get_decision_trace_detail(decision_id: str) -> Dict[str, Any]:
    rt = get_runtime()
    decisions = rt.world.decisions(limit=500)
    decision = next((d for d in decisions if d["decision_id"] == decision_id), None)
    if decision is None:
        raise HTTPException(status_code=404, detail=f"Decision '{decision_id}' not found")

    why = rt.why_blocked(decision_id)
    return {
        "decision": decision,
        "why_blocked": why,
        "provenance_chain": {
            "observations": decision["observations"],
            "belief": decision["belief"],
            "plan": decision["plan"],
            "policy_checks": decision["policy_checks"],
            "action": decision["action"],
            "outcome": decision["outcome"],
        },
    }


# ── Safety, Invariants & Why Blocked ────────────────────────────────────────

@router.get("/safety/status")
def get_safety_status() -> Dict[str, Any]:
    return get_runtime().safety_status()


@router.get("/safety/invariants")
def get_invariants() -> List[Dict[str, Any]]:
    return get_runtime().invariants()


@router.get("/safety/why-blocked/{decision_id}")
def get_why_blocked(decision_id: str) -> Dict[str, Any]:
    why = get_runtime().why_blocked(decision_id)
    if why is None:
        raise HTTPException(status_code=404, detail=f"No block record for decision '{decision_id}'")
    return why


@router.get("/safety/causal-boundary")
def get_causal_boundary() -> Dict[str, Any]:
    rt = get_runtime()
    status = rt.causal_boundary_status()
    self_test = rt.world.boundary_self_test()
    return {
        **status,
        "self_test_evidence": self_test,
    }


# ── Research, Evaluation & Governance ────────────────────────────────────────

@router.get("/evaluation")
def get_evaluation(
    seeds: int = Query(default=5, ge=2, le=20),
    ticks: int = Query(default=20, ge=5, le=100),
    candidate_noise_scale: float = Query(default=0.7, gt=0.0, le=2.0),
) -> Dict[str, Any]:
    return get_runtime().evaluation(
        seeds=seeds,
        ticks=ticks,
        candidate_noise_scale=candidate_noise_scale,
    )


@router.get("/governance")
def get_governance() -> Dict[str, Any]:
    return get_runtime().governance()


@router.get("/evidence")
def get_evidence() -> Dict[str, Any]:
    return get_runtime().evidence()


@router.get("/models")
def get_models() -> Dict[str, Any]:
    return get_runtime().models()


@router.get("/datasets")
def get_datasets() -> Dict[str, Any]:
    return get_runtime().datasets()


@router.get("/policies")
def get_policies() -> Dict[str, Any]:
    return get_runtime().policies()


# ── Scenarios, Search & Report Export ────────────────────────────────────────

@router.get("/scenarios")
def get_scenarios() -> Dict[str, Any]:
    return get_runtime().scenarios_catalog()


@router.post("/scenarios/select")
def select_scenario(req: ScenarioSelectRequest) -> Dict[str, Any]:
    rt = get_runtime(scenario_id=req.scenario_id)
    rt.record_ui_action(req.actor, "SELECT_SCENARIO", req.scenario_id, page="scenarios")
    return rt.overview()


@router.get("/search")
def universal_search(q: str = Query(...), limit: int = 50) -> List[Dict[str, Any]]:
    return get_runtime().search(q, limit=limit)


@router.get("/export-report")
def export_report(format: str = "json") -> Dict[str, Any]:
    return get_runtime().export_report(format=format)


@router.post("/ui-actions")
def record_ui_action(req: UiActionRequest) -> Dict[str, Any]:
    return get_runtime().record_ui_action(
        actor=req.actor,
        action=req.action,
        target=req.target,
        page=req.page,
        detail=req.detail,
        before=req.before,
        after=req.after,
    )


@router.get("/ui-actions")
def get_ui_actions(limit: int = 100) -> List[Dict[str, Any]]:
    return get_runtime().ui_actions(limit=limit)


# ── Live WebSocket Stream ────────────────────────────────────────────────────

@router.websocket("/ws")
async def cockpit_websocket(websocket: WebSocket):
    await websocket.accept()
    rt = get_runtime()
    try:
        while True:
            snapshot = rt.world.snapshot()
            overview = rt.overview()
            payload = {
                "type": "cockpit_tick",
                "tick": snapshot["tick"],
                "run_id": rt.run_id,
                "environment": rt.environment.upper(),
                "world": {
                    "comparison": snapshot["comparison"],
                    "stats": snapshot["stats"],
                    "sensors": snapshot["sensors"],
                    "recent_observations": snapshot["observations"][-10:],
                },
                "summary": {
                    "health_percent": overview["run"]["health_percent"],
                    "playing": overview["run"]["playing"],
                    "speed": overview["run"]["speed"],
                    "alerts_count": len(overview["alerts"]),
                    "policy_blocked": overview["policy"]["blocked"],
                },
            }
            await websocket.send_json(payload)
            await asyncio.sleep(0.5)
    except WebSocketDisconnect:
        pass
    except Exception:
        pass
