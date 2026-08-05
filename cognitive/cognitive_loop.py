# Copyright (c) Ultrone Contributors. All rights reserved.
"""Cognitive Loop — the core decision cycle orchestrator.

Implements the 13-step cognitive loop:

    Perceive → Understand → Update World Model → Retrieve Memory →
    Reason → Predict Futures → Plan → Evaluate → Act →
    Observe Outcome → Learn → Consolidate Memory → Improve Policies

Each phase delegates to one or more pluggable CognitiveLayers. The loop
is event-driven, fault-tolerant, and produces full explainability traces.
"""

from __future__ import annotations

import asyncio
import logging
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence

from .base_layer import CognitiveLayer
from .cycle_context import CycleContext, CyclePhase, PhaseResult
from .event_types import CognitiveEvent, CognitiveEventType, EventBus
from .types import (
    Action,
    ActionOutcome,
    CognitiveContext,
    DecisionTrace,
    Observation,
)

logger = logging.getLogger("Ultrone.Cognitive.Loop")


@dataclass
class CognitiveLoopConfig:
    """Configuration for the cognitive loop."""
    # Layer instances (must be provided by caller)
    layers: Dict[str, CognitiveLayer] = field(default_factory=dict)
    # Safety layer to wrap each phase
    safety_layer: Optional[CognitiveLayer] = None
    # Event bus for internal communication
    event_bus: Optional[EventBus] = None
    # Whether to continue on layer failure
    fail_open: bool = True
    # Maximum cycles before forced consolidation
    max_cycles_before_consolidation: int = 10
    # Resource limits
    cycle_timeout_seconds: float = 60.0
    # Adaptive cycle
    enable_adaptive_loop: bool = True
    # Meta-learning for loop optimization
    enable_loop_meta_learning: bool = True

    def get_layers(self, phase: CyclePhase) -> List[CognitiveLayer]:
        """Find all layers responsible for a given phase."""
        return [
            layer
            for layer in self.layers.values()
            if layer._phase == phase and layer.enabled
        ]


class CognitiveLoop:
    """The central cognitive decision loop.

    Orchestrates the 13-step cognitive cycle by delegating each phase to
    its corresponding CognitiveLayers. Handles error recovery, resource
    limits, explainability trace aggregation, and safety monitoring.

    Parameters
    ----------
    config : CognitiveLoopConfig
        Configuration with layer instances.
    """

    def __init__(self, config: CognitiveLoopConfig):
        self.config = config
        self.event_bus = config.event_bus or EventBus()
        self._layers_by_phase: Dict[CyclePhase, List[CognitiveLayer]] = {}
        self._cycles_run: int = 0
        self._cycles_succeeded: int = 0
        self._cycles_failed: int = 0
        self._decision_traces: List[DecisionTrace] = []
        self._cycle_history: List[CycleContext] = []
        self._safety_violations: List[Dict[str, Any]] = []

        # Register layers by phase (multiple layers per phase supported)
        for name, layer in config.layers.items():
            if layer.enabled:
                if layer._phase not in self._layers_by_phase:
                    self._layers_by_phase[layer._phase] = []
                self._layers_by_phase[layer._phase].append(layer)

    @property
    def phases(self) -> List[CyclePhase]:
        """Ordered list of cognitive loop phases."""
        return list(CyclePhase)

    async def run_cycle(
        self,
        observation: Optional[Observation] = None,
        context: Optional[CognitiveContext] = None,
    ) -> CycleContext:
        """Execute one complete cognitive cycle.

        Parameters
        ----------
        observation : Observation, optional
            Initial observation from the environment. Required for the
            Perceive phase.
        context : CognitiveContext, optional
            Cognitive context (goals, constraints, resources).

        Returns
        -------
        CycleContext
            The fully populated cycle context with all phase results.
        """
        ctx = CycleContext(
            cycle_id=f"cycle-{uuid.uuid4().hex[:12]}",
            context=context or CognitiveContext(),
        )
        self._cycles_run += 1
        cycle_start = time.time()

        if observation:
            ctx.observations.append(observation)

        logger.info("Starting cognitive cycle %s", ctx.cycle_id)

        phase_success = True

        try:
            for phase in self.phases:
                layers = self._layers_by_phase.get(phase, [])

                if not layers:
                    result = PhaseResult(
                        phase=phase,
                        success=True,
                        duration_seconds=0.0,
                        output={"skipped": True, "reason": "no layer for phase"},
                    )
                    ctx.add_phase_result(result)
                else:
                    for layer in layers:
                        phase_start = time.time()

                        # Safety check before each layer
                        if self.config.safety_layer and self.config.safety_layer.enabled:
                            safety_result = self._run_safety_check(ctx, phase)
                            if not safety_result["safe"]:
                                self._record_safety_violation(ctx, phase, safety_result)
                                if not self.config.fail_open:
                                    result = PhaseResult(
                                        phase=phase,
                                        success=False,
                                        duration_seconds=time.time() - phase_start,
                                        error=f"Safety violation: {safety_result['reason']}",
                                    )
                                    ctx.add_phase_result(result)
                                    phase_success = False
                                    break

                        result = layer._wrap_process(ctx)
                        ctx.add_phase_result(result)

                        # Collect decision traces
                        if result.trace:
                            self._decision_traces.append(result.trace)
                            ctx.reasoning_trace = result.trace

                        # Publish event
                        await self._publish_phase_event(ctx, phase, result)

                        if not result.success and not self.config.fail_open:
                            logger.error("Phase %s failed, aborting cycle", phase.value)
                            phase_success = False
                            break

                        if not result.success:
                            phase_success = False

                # Check timeout
                if time.time() - cycle_start > self.config.cycle_timeout_seconds:
                    logger.warning("Cycle %s timed out after %.1fs",
                                   ctx.cycle_id, self.config.cycle_timeout_seconds)
                    ctx.add_phase_result(PhaseResult(
                        phase=phase,
                        success=False,
                        duration_seconds=0.0,
                        output={"timeout": True},
                        error="Cycle timeout exceeded",
                    ))
                    phase_success = False
                    break

            # Post-cycle: aggregate results
            ctx.confidence = self._compute_cycle_confidence(ctx)
            ctx.uncertainty = self._compute_cycle_uncertainty(ctx)

            if phase_success:
                self._cycles_succeeded += 1
            else:
                self._cycles_failed += 1

            ctx.mark_complete()
            self._cycle_history.append(ctx)

            logger.info(
                "Cognitive cycle %s completed in %.3fs (success=%s)",
                ctx.cycle_id,
                time.time() - cycle_start,
                phase_success,
            )

        except Exception as e:
            self._cycles_failed += 1
            logger.error("Cognitive cycle %s failed: %s", ctx.cycle_id, e, exc_info=True)
            ctx.add_phase_result(PhaseResult(
                phase=CyclePhase.LEARN,
                success=False,
                duration_seconds=0.0,
                error=str(e),
            ))
            ctx.mark_complete()

        return ctx

    def _run_safety_check(self, ctx: CycleContext, phase: CyclePhase) -> Dict[str, Any]:
        """Run safety checks before a phase."""
        if not hasattr(self.config.safety_layer, 'check_phase'):
            return {"safe": True, "reason": "no safety checks defined"}
        return self.config.safety_layer.check_phase(ctx, phase)

    def _record_safety_violation(self, ctx: CycleContext, phase: CyclePhase, info: Dict[str, Any]) -> None:
        """Record a safety violation."""
        self._safety_violations.append({
            "cycle_id": ctx.cycle_id,
            "phase": phase.value,
            "timestamp": time.time(),
            "info": info,
        })
        self._publish_event(
            CognitiveEventType.SAFETY_VIOLATION,
            {
                "cycle_id": ctx.cycle_id,
                "phase": phase.value,
                "violation": info,
            },
            source="safety_monitor",
        )

    async def _publish_phase_event(
        self, ctx: CycleContext, phase: CyclePhase, result: PhaseResult
    ) -> None:
        """Publish an event for a completed phase."""
        event_type = self._phase_to_event_type(phase)
        if event_type:
            self._publish_event(
                event_type,
                {
                    "cycle_id": ctx.cycle_id,
                    "phase": phase.value,
                    "success": result.success,
                    "duration": result.duration_seconds,
                    "output": result.output,
                    "trace_id": result.trace.trace_id if result.trace else None,
                },
                source="cognitive_loop",
            )

    def _phase_to_event_type(self, phase: CyclePhase) -> Optional[CognitiveEventType]:
        mapping = {
            CyclePhase.PERCEIVE: CognitiveEventType.PERCEPTION,
            CyclePhase.UNDERSTAND: CognitiveEventType.UNDERSTAND,
            CyclePhase.UPDATE_WORLD_MODEL: CognitiveEventType.WORLD_MODEL_UPDATED,
            CyclePhase.RETRIEVE_MEMORY: CognitiveEventType.MEMORY_RETRIEVED,
            CyclePhase.REASON: CognitiveEventType.REASONING,
            CyclePhase.PREDICT_FUTURES: CognitiveEventType.PREDICTION_GENERATED,
            CyclePhase.PLAN: CognitiveEventType.PLANNING,
            CyclePhase.EVALUATE: CognitiveEventType.EVALUATION,
            CyclePhase.ACT: CognitiveEventType.ACTION_EXECUTED,
            CyclePhase.OBSERVE_OUTCOME: CognitiveEventType.OUTCOME_OBSERVED,
            CyclePhase.LEARN: CognitiveEventType.LEARNING,
            CyclePhase.CONSOLIDATE_MEMORY: CognitiveEventType.MEMORY_CONSOLIDATED,
            CyclePhase.IMPROVE_POLICIES: CognitiveEventType.POLICIES_IMPROVED,
        }
        return mapping.get(phase)

    def _compute_cycle_confidence(self, ctx: CycleContext) -> float:
        """Compute overall cycle confidence from phase results."""
        confidences = []
        for pr in ctx.phase_results:
            if pr.trace and pr.trace.confidence > 0:
                confidences.append(pr.trace.confidence)
            elif pr.success:
                confidences.append(1.0)
            else:
                confidences.append(0.0)
        return sum(confidences) / len(confidences) if confidences else 0.5

    def _compute_cycle_uncertainty(self, ctx: CycleContext) -> float:
        """Compute overall cycle uncertainty."""
        uncertainties = []
        for pr in ctx.phase_results:
            if pr.trace and pr.trace.uncertainty.total > 0:
                uncertainties.append(pr.trace.uncertainty.total)
        if uncertainties:
            return sum(uncertainties) / len(uncertainties)
        # Default based on confidence
        return max(0.0, 1.0 - ctx.confidence)

    def _publish_event(
        self,
        event_type: CognitiveEventType,
        data: Dict[str, Any],
        source: str = "cognitive_loop",
    ) -> None:
        """Publish an event to the event bus."""
        if not self.event_bus:
            return
        event = CognitiveEvent(event_type=event_type, source=source, data=data)
        try:
            self.event_bus.publish_sync(event)
        except Exception as e:
            logger.warning("Event publish failed: %s", e)

    def get_stats(self) -> Dict[str, Any]:
        return {
            "type": "CognitiveLoop",
            "cycles_run": self._cycles_run,
            "cycles_succeeded": self._cycles_succeeded,
            "cycles_failed": self._cycles_failed,
            "decision_traces": len(self._decision_traces),
            "cycle_history": len(self._cycle_history),
            "safety_violations": len(self._safety_violations),
            "layers": {
                phase.value: [layer.name for layer in layers]
                for phase, layers in self._layers_by_phase.items()
            },
        }

    def get_cycles(self) -> List[CycleContext]:
        """Return the history of all cycles."""
        return self._cycle_history

    def get_decision_traces(self) -> List[DecisionTrace]:
        """Return all decision traces from all cycles."""
        return self._decision_traces