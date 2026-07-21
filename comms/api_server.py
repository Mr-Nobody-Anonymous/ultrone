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
    """
    
    def __init__(self, orchestrator: Any, intervention_manager: InterventionManager, host: str = "0.0.0.0", port: int = 8000) -> None:
        self.orchestrator = orchestrator
        self.intervention_manager = intervention_manager
        self.host = host
        self.port = port
        self._server_thread: Optional[threading.Thread] = None
        self._app: Any = None
        self._build_app()
    
    def _build_app(self) -> None:
        """Build FastAPI app with endpoints."""
        try:
            from fastapi import FastAPI
            from fastapi.responses import JSONResponse
            import uvicorn
            
            app = FastAPI(title="ULTRONE Operational API", version="1.0")
            
            @app.get("/status")
            def get_status() -> JSONResponse:
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
                    
                    return JSONResponse({
                        "status": "running",
                        "episode": summary.get("total_episodes", 0),
                        "success_rate": summary.get("success_rate", 0),
                        "mutation_rate": summary.get("final_mutation_rate", 0),
                        "red_survival_rate": 0.0,
                        "latest_briefing": briefing,
                        "active_constraints": constraints,
                    })
                except Exception as e:
                    return JSONResponse({"status": "error", "error": str(e)}, status_code=500)
            
            @app.post("/override")
            def post_override(constraint: Dict[str, Any]) -> JSONResponse:
                """Apply human override constraint."""
                try:
                    self.intervention_manager.add_constraint(constraint)
                    return JSONResponse({"status": "override_applied", "constraint": constraint})
                except Exception as e:
                    return JSONResponse({"status": "error", "error": str(e)}, status_code=500)
            
            @app.post("/clear_constraints")
            def post_clear() -> JSONResponse:
                """Clear all override constraints."""
                try:
                    self.intervention_manager.clear_constraints()
                    return JSONResponse({"status": "constraints_cleared"})
                except Exception as e:
                    return JSONResponse({"status": "error", "error": str(e)}, status_code=500)
            
            @app.post("/ask_reasoning")
            def ask_reasoning() -> JSONResponse:
                """XAI: Get human-readable explanation of best genome."""
                try:
                    best_genome = self.orchestrator.best_genome
                    if not best_genome:
                        return JSONResponse({"explanation": "No best genome available yet."})
                    
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
                    
                    return JSONResponse({"explanation": explanation})
                except Exception as e:
                    return JSONResponse({"explanation": f"Error: {e}"}, status_code=500)
            
            self._app = app
            self._uvicorn = uvicorn
            logger.info("FastAPI app built successfully")
        except Exception as e:
            logger.error(f"Failed to build FastAPI app: {e}")
            self._app = None
    
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

</parameter>
<parameter name="task_progress">
- [x] Install FastAPI and uvicorn
- [ ] Create comms/api_server.py with FastAPI endpoints
- [ ] Create InterventionManager class
- [ ] Update orchestrator to run API in background thread
- [ ] Run tests and push to GitHub
</parameter>
</write_to_file>