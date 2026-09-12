"""Stochastic event scheduling for simulation."""

from __future__ import annotations

import logging
import heapq
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple

from .base import WorldModel, WorldModelConfig

logger = logging.getLogger("Ultrone.Sim.WorldModeling.EventScheduler")


@dataclass
class EventSchedulerConfig(WorldModelConfig):
    """Configuration for event scheduler."""
    max_events_per_tick: int = 10


@dataclass
class SimulationEvent:
    """A scheduled simulation event."""
    tick: int
    priority: int
    name: str
    callback: Callable
    context: Dict[str, Any] = field(default_factory=dict)

    def __lt__(self, other: "SimulationEvent") -> bool:
        return (self.tick, self.priority) < (other.tick, other.priority)


class EventScheduler(WorldModel):
    """Event scheduler for simulation timing and sequencing.

    Manages a priority queue of future events, executing them
    when their scheduled tick arrives.
    """

    def __init__(self, config: Optional[EventSchedulerConfig] = None):
        super().__init__(config or EventSchedulerConfig())
        self._queue: List[SimulationEvent] = []
        self._executed: int = 0

    def schedule(self, event: SimulationEvent) -> None:
        """Add an event to the schedule."""
        heapq.heappush(self._queue, event)

    def schedule_event(self, name: str, delay: int = 0, callback: Optional[Callable] = None, context: Optional[Dict[str, Any]] = None) -> None:
        """Schedule an event by name with a delay.
        
        Args:
            name: Event name/type.
            delay: Number of ticks from now to execute.
            callback: Callback function (defaults to a no-op).
            context: Optional context dict.
        """
        if callback is None:
            callback = lambda **kw: logger.debug("Event '%s' triggered", name)
        self.schedule_in(delay, name, callback, context)

    def schedule_in(self, ticks_from_now: int, name: str, callback: Callable,
                    context: Optional[Dict[str, Any]] = None, priority: int = 0) -> None:
        """Schedule an event N ticks from the current tick."""
        event = SimulationEvent(
            tick=self._tick + ticks_from_now,
            priority=priority,
            name=name,
            callback=callback,
            context=context or {},
        )
        self.schedule(event)

    def update(self, dt: float) -> None:
        self._tick += 1
        count = 0
        while self._queue and self._queue[0].tick <= self._tick and count < self.config.max_events_per_tick:
            event = heapq.heappop(self._queue)
            try:
                event.callback(**event.context)
                self._executed += 1
                logger.debug("Event executed: %s at tick %d", event.name, self._tick)
            except Exception as e:
                logger.error("Event '%s' failed: %s", event.name, e)
            count += 1

    def get_state(self) -> Dict[str, Any]:
        return {
            "pending_events": len(self._queue),
            "executed_events": self._executed,
        }

    def reset(self) -> None:
        super().reset()
        self._queue.clear()
        self._executed = 0
