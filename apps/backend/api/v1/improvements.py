"""Self-improvement API — endpoints for the self-improvement loop."""

import time
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from self_improvement.improvement_loop import SelfImprovementLoop
from self_improvement.telemetry import TelemetryCollector
from self_improvement.hypothesis_generator import HypothesisGenerator

router = APIRouter(prefix="/improvements", tags=["improvements"])

# Shared instances
_improvement_loop = SelfImprovementLoop()
_telemetry = TelemetryCollector()
_hypothesis_generator = HypothesisGenerator()


class TelemetryMetric(BaseModel):
    """Record a telemetry metric."""
    name: str
    value: float


class TelemetryEvent(BaseModel):
    """Record a telemetry event."""
    event_type: str
    details: Dict[str, Any] = {}


class TelemetryFailure(BaseModel):
    """Record a telemetry failure."""
    component: str
    error: str
    details: Dict[str, Any] = {}


@router.post("/run-cycle")
async def run_improvement_cycle() -> Dict[str, Any]:
    """Run a self-improvement cycle."""
    return await _improvement_loop.run_cycle()


@router.get("/stats")
async def get_improvement_stats() -> Dict[str, Any]:
    """Get self-improvement statistics."""
    return _improvement_loop.get_stats()


@router.get("/hypotheses")
async def list_hypotheses() -> List[Dict[str, Any]]:
    """List all generated hypotheses."""
    return _hypothesis_generator.get_hypotheses()


@router.post("/telemetry/metric")
async def record_metric(metric: TelemetryMetric) -> Dict[str, Any]:
    """Record a telemetry metric."""
    _telemetry.record_metric(metric.name, metric.value)
    return {"status": "ok", "metric": metric.name}


@router.post("/telemetry/event")
async def record_event(event: TelemetryEvent) -> Dict[str, Any]:
    """Record a telemetry event."""
    _telemetry.record_event(event.event_type, event.details)
    return {"status": "ok", "event": event.event_type}


@router.post("/telemetry/failure")
async def record_failure(failure: TelemetryFailure) -> Dict[str, Any]:
    """Record a telemetry failure."""
    _telemetry.record_failure(failure.component, failure.error, failure.details)
    return {"status": "ok", "component": failure.component}


@router.get("/telemetry/weaknesses")
async def get_weaknesses() -> List[Dict[str, Any]]:
    """Get identified weaknesses."""
    return _telemetry.identify_weaknesses()


@router.get("/telemetry/stats")
async def get_telemetry_stats() -> Dict[str, Any]:
    """Get telemetry statistics."""
    return _telemetry.get_stats()