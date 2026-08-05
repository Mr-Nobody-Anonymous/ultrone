# Copyright (c) Ultrone Contributors. All rights reserved.
"""Event types and event bus for the cognitive architecture.

All cognitive layers communicate via an internal async event bus, enabling
a decoupled, event-driven architecture where layers can subscribe to
events from other layers and react accordingly.
"""

from __future__ import annotations

import asyncio
import logging
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger("Ultrone.Cognitive.EventBus")


class CognitiveEventType(Enum):
    """Event types published during the cognitive cycle."""

    # Phase events
    PERCEPTION = "cognitive.perception"
    UNDERSTAND = "cognitive.understand"
    WORLD_MODEL_UPDATED = "cognitive.world_model.updated"
    MEMORY_RETRIEVED = "cognitive.memory.retrieved"
    REASONING = "cognitive.reasoning"
    PREDICTION_GENERATED = "cognitive.prediction.generated"
    PLANNING = "cognitive.planning"
    EVALUATION = "cognitive.evaluation"
    ACTION_EXECUTED = "cognitive.action.executed"
    OUTCOME_OBSERVED = "cognitive.outcome.observed"
    LEARNING = "cognitive.learning"
    MEMORY_CONSOLIDATED = "cognitive.memory.consolidated"
    POLICIES_IMPROVED = "cognitive.policies.improved"

    # Sub-system events
    ANOMALY_DETECTED = "cognitive.safety.anomaly"
    UNCERTAINTY_HIGH = "cognitive.uncertainty.high"
    CONFIDENCE_LOW = "cognitive.confidence.low"
    SAFETY_VIOLATION = "cognitive.safety.violation"
    HUMAN_OVERVIEW_REQUESTED = "cognitive.safety.human_review"

    # Meta events
    META_LEARNING_UPDATE = "cognitive.meta.update"
    STRATEGY_SELECTED = "cognitive.strategy.selected"

    @property
    def priority(self) -> int:
        """Higher number = higher priority."""
        _priorities = {
            self.SAFETY_VIOLATION: 100,
            self.HUMAN_OVERVIEW_REQUESTED: 90,
            self.UNCERTAINTY_HIGH: 70,
            self.ANOMALY_DETECTED: 60,
            self.ACTION_EXECUTED: 50,
            self.OUTCOME_OBSERVED: 40,
            self.PERCEPTION: 30,
            self.WORLD_MODEL_UPDATED: 25,
            self.MEMORY_RETRIEVED: 20,
            self.REASONING: 15,
            self.PREDICTION_GENERATED: 15,
            self.PLANNING: 15,
            self.EVALUATION: 10,
            self.LEARNING: 5,
            self.MEMORY_CONSOLIDATED: 5,
            self.POLICIES_IMPROVED: 5,
        }
        return _priorities.get(self, 0)


@dataclass
class CognitiveEvent:
    """A single event in the cognitive architecture."""
    event_id: str = field(default_factory=lambda: f"evt-{uuid.uuid4().hex[:12]}")
    event_type: CognitiveEventType = CognitiveEventType.PERCEPTION
    source: str = "unknown"
    timestamp: float = field(default_factory=time.time)
    data: Dict[str, Any] = field(default_factory=dict)
    priority: int = 0
    correlation_id: str = field(default_factory=lambda: f"corr-{uuid.uuid4().hex[:12]}")
    reply_to: Optional[str] = None

    def __post_init__(self):
        if self.priority == 0:
            self.priority = self.event_type.priority

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "event_type": self.event_type.value,
            "source": self.source,
            "timestamp": self.timestamp,
            "data": self.data,
            "priority": self.priority,
            "correlation_id": self.correlation_id,
            "reply_to": self.reply_to,
        }


@dataclass
class PerceptionEvent:
    """Event published when perception completes."""
    event_id: str
    timestamp: float
    scene_graph: Dict[str, Any]
    observations: List[Dict[str, Any]]
    confidence: float
    uncertainty: float
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class WorldModelUpdateEvent:
    """Event published when the world model is updated."""
    event_id: str
    timestamp: float
    updated_entities: List[str]
    predicted_futures: List[Dict[str, Any]]
    confidence: float
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class MemoryRetrievalEvent:
    """Event published when memory is retrieved."""
    event_id: str
    timestamp: float
    query: str
    results_count: int
    sources: List[str]
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ReasoningEvent:
    """Event published after reasoning completes."""
    event_id: str
    timestamp: float
    strategy: str
    result: str
    confidence: float
    trace_id: str
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PlanningEvent:
    """Event published after planning completes."""
    event_id: str
    timestamp: float
    plan_id: str
    goal: str
    steps_count: int
    planner_type: str
    confidence: float
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ActionExecutionEvent:
    """Event published after an action is executed."""
    event_id: str
    timestamp: float
    action_id: str
    action_name: str
    success: bool
    outcome: Dict[str, Any]
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class LearningEvent:
    """Event published after learning completes."""
    event_id: str
    timestamp: float
    learning_type: str  # online, continual, transfer, meta, rl, imitation, evolutionary
    models_updated: List[str]
    metrics: Dict[str, float] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SelfReflectionEvent:
    """Event published after self-reflection."""
    event_id: str
    timestamp: float
    evaluations: Dict[str, float]
    lessons_learned: List[str]
    policy_improvements: List[Dict[str, Any]]
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class MetaLearningEvent:
    """Event published after meta-learning adaptation."""
    event_id: str
    timestamp: float
    adaptations: List[Dict[str, Any]]
    improvement: float
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SafetyEvent:
    """Event published by safety monitors."""
    event_id: str
    timestamp: float
    monitor_name: str
    alert_type: str
    severity: str
    details: Dict[str, Any]
    recommended_action: str
    metadata: Dict[str, Any] = field(default_factory=dict)


class EventBus:
    """Async event bus for internal cognitive architecture communication.

    Features:
    - Topic-based publish/subscribe
    - Priority-based delivery
    - Event history for replay and auditing
    - Async and sync handler support
    """

    def __init__(self, max_history: int = 5000):
        self.max_history = max_history
        self._subscribers: Dict[str, List[Callable]] = {}
        self._history: List[CognitiveEvent] = []
        self._running = False

    def subscribe(self, event_type: CognitiveEventType, handler: Callable) -> None:
        """Register a handler for a specific event type."""
        key = event_type.value
        if key not in self._subscribers:
            self._subscribers[key] = []
        self._subscribers[key].append(handler)

    def subscribe_any(self, handler: Callable) -> None:
        """Register a handler for all event types."""
        if "*" not in self._subscribers:
            self._subscribers["*"] = []
        self._subscribers["*"].append(handler)

    def unsubscribe(self, event_type: CognitiveEventType, handler: Callable) -> None:
        """Remove a handler for a specific event type."""
        key = event_type.value
        if key in self._subscribers:
            try:
                self._subscribers[key].remove(handler)
            except ValueError:
                pass

    async def publish(self, event: CognitiveEvent) -> None:
        """Publish an event to all matching subscribers."""
        self._history.append(event)
        if len(self._history) > self.max_history:
            self._history = self._history[-self.max_history:]

        # Deliver to specific subscribers
        key = event.event_type.value
        handlers = list(self._subscribers.get(key, []))
        wildcard_handlers = list(self._subscribers.get("*", []))

        for handler in handlers + wildcard_handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(event)
                else:
                    handler(event)
            except Exception as e:
                logger.error("Handler error for %s: %s", event.event_type.value, e, exc_info=True)

    def publish_sync(self, event: CognitiveEvent) -> None:
        """Synchronously publish an event (for testing and sync contexts)."""
        self._history.append(event)
        if len(self._history) > self.max_history:
            self._history = self._history[-self.max_history:]

        key = event.event_type.value
        handlers = list(self._subscribers.get(key, []))
        wildcard_handlers = list(self._subscribers.get("*", []))

        for handler in handlers + wildcard_handlers:
            try:
                handler(event)
            except Exception as e:
                logger.error("Sync handler error for %s: %s", event.event_type.value, e, exc_info=True)

    def get_history(
        self,
        event_type: Optional[CognitiveEventType] = None,
        limit: int = 100,
    ) -> List[CognitiveEvent]:
        """Retrieve recent event history."""
        if event_type:
            events = [e for e in self._history if e.event_type == event_type]
        else:
            events = list(self._history)
        return events[-limit:]

    def get_stats(self) -> Dict[str, Any]:
        return {
            "type": "EventBus",
            "history_size": len(self._history),
            "subscriber_types": len(self._subscribers),
            "running": self._running,
        }

    async def start(self) -> None:
        self._running = True

    async def stop(self) -> None:
        self._running = False
