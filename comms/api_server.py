# Copyright (c) Ultrone Contributors. All rights reserved.
"""
Operational Command API Server - FastAPI asynchronous server.

Provides HITL controls and XAI endpoints for ULTRONE.
Runs in a background thread without blocking the evolutionary loop.
"""

from __future__ import annotations

import logging
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("Ultrone.Comms.APIServer")

# Default output path for briefings
BRIEFING_LOG_PATH = Path(__file__).resolve().parent.parent / "memory" / "commander_log.txt"


class InterventionManager:
    """
    Manages human-in-the-loop interventions for the evolutionary engine.
    
    Stores override constraints that are checked at the start of each generation.
    """
    
    def __init__(self) -> None:
        self._constraints: Dict[str, Any] = {}
        self._lock = threading.Lock()
    
    def add_constraint(self, constraint: Dict[str, Any]) -> None:
        """Add a new constraint override."""
        with self._lock:
            self._constraints.update(constraint)
            logger.info(f"Constraint added: {constraint}")
    
    def clear_constraints(self) -> None:
        """Clear all active constraints."""
        with self._lock:
            self._constraints.clear()
            logger.info("All constraints cleared")
    
    def get_constraints(self) -> Dict[str, Any]:
        """Get current constraints (thread-safe)."""
        with self._lock:
            return dict(self._constraints)
    
    def has_constraint(self, key: str) -> bool:
        """Check if a specific constraint exists."""
        with self._lock:
            return key in self._constraints


class APIServer:
    """
    FastAPI server for operational command and XAI.
    
    Runs in a background thread. Endpoints:
    - GET /status: Current training status
    - POST /override: Human override constraints
    - POST /ask_reasoning: XAI explanation of best genome
    - GET /analysis: Current battlefield analysis snapshot
    - GET /map/3d: 3D scene JSON for the frontend renderer
    - WS /ws: Live WebSocket broadcast of telemetry + world state + analysis
    """
    
    def __init__(self, orchestrator: Any, intervention_manager: InterventionManager, host: str = "0.0.0.0", port: int = 8000) -> None:
        self.orchestrator = orchestrator
        self.intervention_manager = intervention_manager
        self.host = host
        self.port = port
        self._server_thread: Optional[threading.Thread] = None
        self._app: Any = None
        self._analysis_cache: Dict[str, Any] = {}
        self._ws_clients: List[Any] = []
        self._ws_lock = threading.Lock()
        self._build_app()
    
    def _build_app(self) -> None:
        """Build FastAPI app with endpoints."""
        try:
            from fastapi import FastAPI
            import uvicorn
            
            app = FastAPI(title="ULTRONE Operational API", version="1.0")
            
            @app.get("/status")
            def get_status() -> Any:
                """Return current training status."""
                try:
                    summary = self.orchestrator.get_training_summary()
                    constraints = self.intervention_manager.get_constraints()
                    
                    # Get latest briefing
                    briefing = ""
                    try:
                        if BRIEFING_LOG_PATH.exists():
                            with open(BRIEFING_LOG_PATH, "r", encoding="utf-8") as f:
                                lines = f.readlines()
                                for line in reversed(lines):
                                    if "TACTICAL BRIEFING" in line:
                                        briefing = line.strip()
                                        break
                    except Exception:
                        pass
                    
                    return {
                        "status": "running",
                        "episode": summary.get("total_episodes", 0),
                        "success_rate": summary.get("success_rate", 0),
                        "mutation_rate": summary.get("final_mutation_rate", 0),
                        "red_survival_rate": 0.0,
                        "latest_briefing": briefing,
                        "active_constraints": constraints,
                    }
                except Exception as e:
                    return {"status": "error", "error": str(e)}
            
            @app.post("/override")
            def post_override(constraint: Dict[str, Any]) -> Any:
                """Apply human override constraint."""
                try:
                    self.intervention_manager.add_constraint(constraint)
                    return {"status": "override_applied", "constraint": constraint}
                except Exception as e:
                    return {"status": "error", "error": str(e)}
            
            @app.post("/clear_constraints")
            def post_clear() -> Any:
                """Clear all override constraints."""
                try:
                    self.intervention_manager.clear_constraints()
                    return {"status": "constraints_cleared"}
                except Exception as e:
                    return {"status": "error", "error": str(e)}
            
            @app.post("/ask_reasoning")
            def ask_reasoning() -> Any:
                """XAI: Get human-readable explanation of best genome."""
                try:
                    best_genome = self.orchestrator.best_genome
                    if not best_genome:
                        return {"explanation": "No best genome available yet."}
                    
                    # Build genome description
                    action_weights = getattr(best_genome, 'action_weights', {})
                    top_actions = sorted(action_weights.items(), key=lambda x: x[1], reverse=True)[:3]
                    action_desc = ", ".join([f"{a}:{w:.2f}" for a, w in top_actions])
                    
                    explanation = (
                        f"Best genome {best_genome.genome_id} (gen {best_genome.generation})\n"
                        f"Top actions: {action_desc}\n"
                        f"Fitness: {best_genome.fitness_score:.3f}\n\n"
                        f"This genome has learned to {_interpret_actions(top_actions)}. "
                        f"The evolutionary algorithm discovered that prioritizing "
                        f"{top_actions[0][0] if top_actions else 'unknown'} "
                        f"yields the highest reward in this adversarial environment."
                    )
                    
                    return {"explanation": explanation}
                except Exception as e:
                    return {"explanation": f"Error: {e}"}

            @app.get("/analysis")
            def get_analysis() -> Any:
                """Return the latest battlefield analysis snapshot."""
                try:
                    if not self._analysis_cache:
                        return {"status": "no_analysis", "message": "Analysis not yet available. Run a training episode first."}
                    return {"status": "ok", "analysis": self._analysis_cache}
                except Exception as e:
                    return {"status": "error", "error": str(e)}

            @app.get("/map/3d")
            def get_map_3d() -> Any:
                """Return the 3D battlefield scene JSON for the frontend."""
                try:
                    scene = self._get_3d_scene()
                    return {"status": "ok", "scene": scene}
                except Exception as e:
                    return {"status": "error", "error": str(e)}

            @app.websocket("/ws")
            async def websocket_endpoint(websocket: Any) -> None:
                """Live WebSocket - broadcast telemetry, world state & analysis."""
                await websocket.accept()
                with self._ws_lock:
                    self._ws_clients.append(websocket)
                try:
                    while True:
                        # Keep alive: wait for client messages, respond with latest state
                        await websocket.receive_text()
                        payload = self._build_broadcast_payload()
                        await websocket.send_json(payload)
                except Exception:
                    pass
                finally:
                    with self._ws_lock:
                        if websocket in self._ws_clients:
                            self._ws_clients.remove(websocket)
            
            self._app = app
            self._uvicorn = uvicorn
            logger.info("FastAPI app built successfully (with analysis + 3D map + WebSocket)")
        except Exception as e:
            logger.error(f"Failed to build FastAPI app: {e}")
            self._app = None

    # ------------------------------------------------------------------
    # Analysis / scene helpers
    # ------------------------------------------------------------------

    def _get_3d_scene(self) -> Dict[str, Any]:
        """Build the 3D scene from the orchestrator's environment state."""
        # Check if orchestrator has analysis components
        if hasattr(self.orchestrator, 'battlefield_3d'):
            scene = self.orchestrator.battlefield_3d.export_scene(
                units=getattr(self.orchestrator, 'last_units', None),
                contacts=getattr(self.orchestrator, 'last_contacts', None),
                grid_size=(100, 100),
            )
            return scene

        # Fallback: build scene from env observation if available
        env = getattr(self.orchestrator, '_current_env', None)
        if env is None:
            return {"status": "unavailable", "message": "No battlefield environment available."}

        try:
            obs = env._get_observation()
            from brain.perception.battlefield_3d import Battlefield3DExporter
            exporter = Battlefield3DExporter()
            scene = exporter.export_scene(
                units=_entities_from_observation(obs),
                grid_size=(100, 100),
            )
            return scene
        except Exception as e:
            logger.error(f"3D scene build failed: {e}")
            return {"status": "error", "error": str(e)}

    def _build_broadcast_payload(self) -> Dict[str, Any]:
        """Build the WebSocket broadcast payload with latest state."""
        payload: Dict[str, Any] = {
            "type": "status",
            "payload": {
                "telemetry": self.orchestrator.get_training_summary() if hasattr(self.orchestrator, 'get_training_summary') else {},
                "analysis": self._analysis_cache,
            },
        }
        return payload

    def publish_analysis(self, analysis: Dict[str, Any]) -> None:
        """Store the latest analysis for REST polling and WS broadcast."""
        self._analysis_cache = analysis

    def broadcast(self, message: Dict[str, Any]) -> None:
        """Broadcast a message to all connected WebSocket clients (best-effort)."""
        with self._ws_lock:
            clients = list(self._ws_clients)

        for client in clients:
            try:
                import asyncio
                loop = asyncio.new_event_loop()
                loop.run_until_complete(client.send_json(message))
                loop.close()
            except Exception:
                # Client likely disconnected; drop silently
                pass

    def start(self) -> None:
        """Start API server in background thread."""
        if self._app is None:
            logger.warning("API server not available")
            return
        
        def run_server():
            try:
                self._uvicorn.run(self._app, host=self.host, port=self.port, log_level="warning")
            except Exception as e:
                logger.error(f"API server error: {e}")
        
        self._server_thread = threading.Thread(target=run_server, daemon=True)
        self._server_thread.start()
        logger.info(f"Operational API live on http://localhost:{self.port}")
    
    def stop(self) -> None:
        """Stop API server."""
        if self._server_thread and self._server_thread.is_alive():
            # Uvicorn doesn't have a clean shutdown from thread, but daemon thread will exit with main process
            logger.info("API server stopping (daemon thread)")


def create_api_server(orchestrator: Any, intervention_manager: InterventionManager) -> Optional[APIServer]:
    """Create and return API server instance."""
    try:
        server = APIServer(orchestrator, intervention_manager)
        return server
    except Exception as e:
        logger.error(f"Failed to create API server: {e}")
        return None


def _interpret_actions(top_actions: List[tuple]) -> str:
    """Interpret top actions for XAI explanation."""
    if not top_actions:
        return "no dominant actions"
    
    action_names = [a[0] for a in top_actions]
    if "strike" in action_names and "jam" in action_names:
        return "combine precision strikes with electronic warfare to suppress Red defenses"
    elif "strike" in action_names:
        return "prioritize direct kinetic engagement to eliminate Red Force"
    elif "jam" in action_names:
        return "disrupt Red coordination through electronic warfare"
    elif "move" in action_names:
        return "maneuver to optimal engagement positions"
    else:
        return "execute a balanced multi-action strategy"


def _entities_from_observation(obs: Dict[str, Any]) -> List[Any]:
    """Convert a BattlefieldEnv observation into entity-like objects.

    Builds minimal unit-like objects with team, position, health, and type
    attributes that the BattlefieldAnalyzer can consume.
    """
    class _Entity:
        def __init__(self, eid: str, team: str, position: Any, health: float, etype: str):
            self.unit_id = eid
            self.team = team
            self.position = position
            self.health = health
            self.unit_type = etype
            self.capability = 1.0

    entities: List[Any] = []

    # Red force
    red = obs.get("red_force", {})
    if red:
        entities.append(_Entity(
            eid="red_force_main",
            team="red",
            position=red.get("position", (50, 50)),
            health=red.get("health", 100),
            etype=red.get("type", "unknown"),
        ))

    # Blue assets
    blue = obs.get("blue_assets", {})
    for asset_type, assets in blue.items():
        for i, asset in enumerate(assets):
            entities.append(_Entity(
                eid=f"{asset_type}_{i}",
                team="blue",
                position=asset.get("position", (50, 50)),
                health=asset.get("health", 100),
                etype=asset_type,
            ))

    # Supply nodes (neutral infrastructure)
    supply_nodes = obs.get("supply_nodes", {})
    for sid, sn in supply_nodes.items():
        entities.append(_Entity(
            eid=sid,
            team=sn.get("team", "neutral"),
            position=sn.get("position", (50, 50)),
            health=sn.get("health", 100),
            etype="supply_node",
        ))

    return entities
