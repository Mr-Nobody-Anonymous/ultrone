# Copyright (c) Ultrone Contributors. All rights reserved.
"""Base interfaces for all cognitive layers.

Every cognitive layer implements a standard interface so that layers can be
swapped, composed, and tested independently. Each layer is event-driven and
produces explainability traces.
"""

from __future__ import annotations

import logging
import time
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .cycle_context import CycleContext, CyclePhase, PhaseResult
from .event_types import CognitiveEvent, CognitiveEventType, EventBus
from .types import DecisionTrace

logger = logging.getLogger("Ultrone.Cognitive.BaseLayer")


@dataclass
class LayerConfig:
    """Base configuration for cognitive layers."""
    name: str = "base"
    enabled: bool = True
    event_bus: Optional[EventBus] = None
    explainability_enabled: bool = True
    safety_monitoring_enabled: bool = True
    timeout_seconds: float = 30.0
    metadata: Dict[str, Any] = field(default_factory=dict)


class CognitiveLayer(ABC):
    """Abstract base class for all cognitive layers.

    Each layer:
    1. Receives a CycleContext
    2. Performs its phase of the cognitive cycle
    3. Publishes events to the event bus
    4. Records a PhaseResult with optional DecisionTrace
    5. Updates the CycleContext with its outputs
    """

    def __init__(self, config: LayerConfig):
        self.config = config
        self.event_bus = config.event_bus
        self.name = config.name
        self.enabled = config.enabled
        self._phase = self._layer_phase()
        self._call_count = 0
        self._total_duration = 0.0

    @abstractmethod
    def _layer_phase(self) -> CyclePhase:
        """Return the CyclePhase this layer is responsible for."""
        ...

    @abstractmethod
    def process(self, ctx: CycleContext) -> PhaseResult:
        """Execute this layer's phase on the cycle context.

        Parameters
        ----------
        ctx : CycleContext
            The shared cycle context.

        Returns
        -------
        PhaseResult
            Result of this layer's processing.
        """
        ...

    def _publish_event(
        self,
        event_type: CognitiveEventType,
        data: Dict[str, Any],
        source: Optional[str] = None,
    ) -> Optional[CognitiveEvent]:
        """Publish an event to the event bus if one is configured."""
        if not self.event_bus:
            return None
        event = CognitiveEvent(
            event_type=event_type,
            source=source or self.name,
            data=data,
        )
        # Use sync publish for simplicity; layers can override for async
        try:
            self.event_bus.publish_sync(event)
        except Exception as e:
            logger.warning("Event publish failed for %s: %s", self.name, e)
        return event

    def _create_trace(
        self,
        decision: str,
        confidence: float,
        evidence: Optional[List[Dict[str, Any]]] = None,
    ) -> DecisionTrace:
        """Create a decision trace for explainability."""
        trace = DecisionTrace(
            decision=decision,
            confidence=confidence,
            cycle_phase=self._phase.value,
        )
        from .types import Evidence
        if evidence:
            for ev in evidence:
                trace.add_evidence(Evidence(
                    source=ev.get("source", "unknown"),
                    description=ev.get("description", ""),
                    confidence=ev.get("confidence", 1.0),
                    weight=ev.get("weight", 1.0),
                ))
        return trace

    def _wrap_process(self, ctx: CycleContext) -> PhaseResult:
        """Wrapper that handles timing, error handling, and event publishing."""
        if not self.enabled:
            return PhaseResult(
                phase=self._phase,
                success=True,
                duration_seconds=0.0,
                output={"skipped": True, "reason": "layer disabled"},
            )

        start = time.time()
        self._call_count += 1
        try:
            result = self.process(ctx)
            self._total_duration += result.duration_seconds
            return result
        except Exception as e:
            duration = time.time() - start
            self._total_duration += duration
            logger.error("Layer %s failed during %s: %s", self.name, self._phase.value, e, exc_info=True)
            return PhaseResult(
                phase=self._phase,
                success=False,
                duration_seconds=duration,
                error=str(e),
            )

    def get_stats(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "type": type(self).__name__,
            "enabled": self.enabled,
            "call_count": self._call_count,
            "total_duration_seconds": self._total_duration,
            "avg_duration_seconds": (
                self._total_duration / max(1, self._call_count)
            ),
        }
