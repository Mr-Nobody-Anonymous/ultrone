"""Simulation control API - live state management."""

import asyncio
import json
import time
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from pydantic import BaseModel

router = APIRouter()

# Active WebSocket connections for live streaming
active_connections: List[WebSocket] = []

# Current simulation state (populated by orchestrator)
simulation_state: Dict[str, Any] = {
    "status": "idle",
    "episode": 0,
    "total_episodes": 1000,
    "telemetry": [],
    "world_state": None,
}


class SimulationCommand(BaseModel):
    """Command to control simulation."""
    action: str  # start, pause, stop, reset, speed
    value: Optional[Any] = None


class ConfigUpdate(BaseModel):
    """Update simulation configuration."""
    algorithm: Optional[Dict[str, str]] = None  # category -> algorithm
    params: Optional[Dict[str, Any]] = None


@router.post("/command")
async def simulation_command(cmd: SimulationCommand) -> Dict[str, Any]:
    """Send a command to the simulation engine."""
    global simulation_state
    if cmd.action == "start":
        simulation_state["status"] = "running"
    elif cmd.action == "pause":
        simulation_state["status"] = "paused"
    elif cmd.action == "stop":
        simulation_state["status"] = "idle"
    elif cmd.action == "speed" and cmd.value:
        simulation_state["speed"] = float(cmd.value)
    return {"status": simulation_state["status"]}


@router.get("/state")
async def get_simulation_state() -> Dict[str, Any]:
    """Get current simulation state."""
    return simulation_state


@router.post("/config")
async def update_config(config: ConfigUpdate) -> Dict[str, Any]:
    """Update algorithm configuration at runtime."""
    if config.algorithm:
        for category, algo in config.algorithm.items():
            simulation_state.setdefault("active_algorithms", {})[category] = algo
    if config.params:
        simulation_state.update(config.params)
    return {"applied": True}


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket for live telemetry streaming."""
    await websocket.accept()
    active_connections.append(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            # Handle incoming commands from frontend
            try:
                cmd = json.loads(data)
                if cmd.get("action") == "ping":
                    await websocket.send_json({"type": "pong", "timestamp": time.time()})
            except json.JSONDecodeError:
                pass
    except WebSocketDisconnect:
        active_connections.remove(websocket)


async def broadcast_telemetry(telemetry: Dict[str, Any]):
    """Broadcast telemetry to all connected clients."""
    message = json.dumps({"type": "telemetry", "payload": telemetry})
    for conn in active_connections:
        try:
            await conn.send_text(message)
        except Exception:
            pass


async def broadcast_world_state(state: Dict[str, Any]):
    """Broadcast world state update."""
    message = json.dumps({"type": "world_state", "payload": state})
    for conn in active_connections:
        try:
            await conn.send_text(message)
        except Exception:
            pass
