"""Experiment management API."""

import time
import uuid
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter()

# In-memory experiment store
experiments: Dict[str, Dict[str, Any]] = {}


class ExperimentConfig(BaseModel):
    """Configuration for a new experiment."""
    name: str
    description: Optional[str] = ""
    algorithm_selection: Dict[str, str] = {}
    hyperparameters: Dict[str, Any] = {}
    n_episodes: int = 100
    max_steps: int = 500


class ExperimentRun(BaseModel):
    """A single experiment run result."""
    id: str
    config: ExperimentConfig
    status: str = "pending"
    metrics: Dict[str, Any] = {}
    created_at: float = 0.0
    completed_at: Optional[float] = None


@router.post("/")
async def create_experiment(config: ExperimentConfig) -> ExperimentRun:
    """Create a new experiment."""
    exp_id = str(uuid.uuid4())[:8]
    run = ExperimentRun(
        id=exp_id,
        config=config,
        status="created",
        created_at=time.time(),
    )
    experiments[exp_id] = run.dict()
    return run


@router.get("/")
async def list_experiments() -> List[ExperimentRun]:
    """List all experiments."""
    return [ExperimentRun(**e) for e in experiments.values()]


@router.get("/{exp_id}")
async def get_experiment(exp_id: str) -> ExperimentRun:
    """Get a specific experiment."""
    exp = experiments.get(exp_id)
    if not exp:
        raise HTTPException(404, f"Experiment {exp_id} not found")
    return ExperimentRun(**exp)


@router.post("/{exp_id}/run")
async def run_experiment(exp_id: str) -> ExperimentRun:
    """Run an experiment (simulated)."""
    exp = experiments.get(exp_id)
    if not exp:
        raise HTTPException(404, f"Experiment {exp_id} not found")
    exp["status"] = "running"
    # Simulate execution
    exp["metrics"] = {
        "final_reward": 85.3,
        "avg_reward": 72.1,
        "success_rate": 0.78,
        "avg_episode_length": 342,
        "total_steps": exp["config"]["n_episodes"] * exp["config"]["max_steps"],
        "wall_time_s": 12.5,
    }
    exp["status"] = "completed"
    exp["completed_at"] = time.time()
    return ExperimentRun(**exp)
