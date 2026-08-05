# Copyright (c) Ultrone Contributors. All rights reserved.
"""Cycle context — the data object that flows through the cognitive loop.

Each phase of the cognitive loop reads from and writes to a ``CycleContext``,
which serves as the shared memory and decision record for a single
cognitive cycle (Perceive → … → Improve Policies).
"""

from __future__ import annotations

import logging
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

from .types import (
    Action,
    ActionOutcome,
    CognitiveContext,
    DecisionTrace,
    Observation,
    Plan,
    PredictionResult,
    SceneGraph,
    SituationalContext,
    WorldState,
    FuturePrediction,
)

logger = logging.getLogger("Ultrone.Cognitive.CycleContext")


class CyclePhase(Enum):
    """The 13 phases of the cognitive loop."""
    PERCEIVE = "perceive"
    UNDERSTAND = "understand"
    UPDATE_WORLD_MODEL = "update_world_model"
    RETRIEVE_MEMORY = "retrieve_memory"
    REASON = "reason"
    PREDICT_FUTURES = "predict_futures"
    PLAN = "plan"
    EVALUATE = "evaluate"
    ACT = "act"
    OBSERVE_OUTCOME = "observe_outcome"
    LEARN = "learn"
    CONSOLIDATE_MEMORY = "consolidate_memory"
    IMPROVE_POLICIES = "improve_policies"

    @property
    def next_phase(self) -> "CyclePhase":
        order = list(CyclePhase)
        idx = order.index(self)
        return order[(idx + 1) % len(order)]

    @property
    def is_terminal(self) -> bool:
        return self == CyclePhase.IMPROVE_POLICIES


@dataclass
class PhaseResult:
    """Result of executing a single phase of the cognitive loop."""
    phase: CyclePhase
    success: bool
    duration_seconds: float
    output: Dict[str, Any] = field(default_factory=dict)
    trace: Optional[DecisionTrace] = None
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "phase": self.phase.value,
            "success": self.success,
            "duration_seconds": self.duration_seconds,
            "output_keys": list(self.output.keys()),
            "has_trace": self.trace is not None,
            "error": self.error,
        }


@dataclass
class CycleContext:
    """Shared context that flows through one complete cognitive cycle.

    Attributes
    ----------
    cycle_id : str
        Unique identifier for this cognitive cycle.
    context : CognitiveContext
        The overarching cognitive context (goals, constraints, resources).
    observations : list of Observation
        Raw multimodal observations from perception.
    scene_graph : SceneGraph
        Fused probabilistic scene graph from perception.
    situational_context : SituationalContext
        Understanding of objects, relationships, events, conditions.
    world_state : WorldState
        Current world model snapshot.
    predicted_futures : list of FuturePrediction
        Short-term, long-term, alternative, and counterfactual predictions.
    memory_retrievals : list of dict
        Results from memory retrieval across all memory layers.
    reasoning_trace : DecisionTrace
        Trace of the reasoning process.
    plan : Plan
        Selected plan for action.
    actions : list of Action
        Actions derived from the plan.
    action_outcomes : list of ActionOutcome
        Observed outcomes of executed actions.
    learnings : list of dict
        Learning updates from this cycle.
    self_reflection : dict
        Self-reflection evaluation results.
    confidence : float
        Overall confidence in this cycle's decisions.
    uncertainty : float
        Overall uncertainty estimate.
    phase_results : list of PhaseResult
        Results from each phase that was executed.
    metadata : dict
        Arbitrary metadata.
    """
    cycle_id: str = field(default_factory=lambda: f"cycle-{uuid.uuid4().hex[:12]}")
    context: CognitiveContext = field(default_factory=CognitiveContext)
    observations: List[Observation] = field(default_factory=list)
    scene_graph: Optional[SceneGraph] = None
    situational_context: Optional[SituationalContext] = None
    world_state: Optional[WorldState] = None
    predicted_futures: List[FuturePrediction] = field(default_factory=list)
    memory_retrievals: List[Dict[str, Any]] = field(default_factory=list)
    reasoning_trace: Optional[DecisionTrace] = None
    plan: Optional[Plan] = None
    actions: List[Action] = field(default_factory=list)
    action_outcomes: List[ActionOutcome] = field(default_factory=list)
    learnings: List[Dict[str, Any]] = field(default_factory=list)
    self_reflection: Dict[str, Any] = field(default_factory=dict)
    confidence: float = 1.0
    uncertainty: float = 0.0
    phase_results: List[PhaseResult] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    started_at: float = field(default_factory=time.time)
    completed_at: Optional[float] = None

    def get_phase_result(self, phase: CyclePhase) -> Optional[PhaseResult]:
        """Retrieve the result of a specific phase."""
        for pr in self.phase_results:
            if pr.phase == phase:
                return pr
        return None

    def add_phase_result(self, result: PhaseResult) -> None:
        """Record a phase result."""
        self.phase_results.append(result)

    def mark_complete(self) -> None:
        """Mark the cycle as complete and record the completion time."""
        self.completed_at = time.time()
        logger.debug("Cycle %s completed in %.3fs", self.cycle_id,
                     self.completed_at - self.started_at)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "cycle_id": self.cycle_id,
            "context": self.context.to_dict(),
            "observations_count": len(self.observations),
            "has_scene_graph": self.scene_graph is not None,
            "has_situational_context": self.situational_context is not None,
            "has_world_state": self.world_state is not None,
            "predicted_futures_count": len(self.predicted_futures),
            "memory_retrievals_count": len(self.memory_retrievals),
            "has_reasoning_trace": self.reasoning_trace is not None,
            "has_plan": self.plan is not None,
            "actions_count": len(self.actions),
            "action_outcomes_count": len(self.action_outcomes),
            "learnings_count": len(self.learnings),
            "has_self_reflection": bool(self.self_reflection),
            "confidence": self.confidence,
            "uncertainty": self.uncertainty,
            "phase_results": [pr.to_dict() for pr in self.phase_results],
            "metadata": self.metadata,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
        }
