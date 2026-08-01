"""Stochastic random events for simulation variability."""

from __future__ import annotations

import logging
import numpy as np
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple

from .base import WorldModel, WorldModelConfig

logger = logging.getLogger("Ultrone.Sim.WorldModeling.StochasticEvents")


@dataclass
class StochasticEventConfig(WorldModelConfig):
    """Configuration for stochastic event generator."""
    event_probability: float = 0.02  # per tick
    events: List[str] = field(default_factory=lambda: [
        "equipment_failure", "civilian_presence", "iwd_attack",
        "air_strike", "chemical_hazard", "communication_outage",
        "reinforcement_arrival", "supply_drop",
    ])


class StochasticEventGenerator(WorldModel):
    """Generates random battlefield events for simulation variability.

    Events can be used to test agent robustness and adaptability.
    Each event has configurable probability and can be handled
    by registered callbacks.
    """

    def __init__(self, config: Optional[StochasticEventConfig] = None):
        super().__init__(config or StochasticEventConfig())
        self._listeners: Dict[str, List[Callable]] = {e: [] for e in self.config.events}
        self._active_events: List[Dict[str, Any]] = []

    def register_listener(self, event_type: str, callback: Callable) -> None:
        """Register a callback for a specific event type."""
        if event_type in self._listeners:
            self._listeners[event_type].append(callback)

    def generate(self) -> Dict[str, Any]:
        """Generate a random battlefield event.
        
        Returns:
            Dict with event data, or empty dict if no event generated.
        """
        if np.random.random() < self.config.event_probability:
            event_type = np.random.choice(self.config.events)
            event_data = {
                "type": event_type,
                "tick": self._tick,
                "position": (np.random.randint(0, 100), np.random.randint(0, 100)),
                "severity": np.random.uniform(0.3, 1.0),
            }
            self._active_events.append(event_data)
            logger.info("Stochastic event: %s at tick %d", event_type, self._tick)
            for callback in self._listeners.get(event_type, []):
                try:
                    callback(event_data)
                except Exception as e:
                    logger.error("Event callback failed: %s", e)
            return event_data
        return {}

    def update(self, dt: float) -> None:
        self._tick += 1
        self.generate()

    def get_state(self) -> Dict[str, Any]:
        return {
            "active_events": len(self._active_events),
            "recent_events": self._active_events[-5:] if self._active_events else [],
        }
