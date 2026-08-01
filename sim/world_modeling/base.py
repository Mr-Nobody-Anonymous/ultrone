"""Base class for all world models."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, Optional


@dataclass
class WorldModelConfig:
    """Base configuration for all world models."""
    name: str = "world_model"
    seed: int = 42
    enabled: bool = True


class WorldModel(ABC):
    """Abstract base class for all world models."""

    def __init__(self, config: WorldModelConfig):
        self.config = config
        self._tick: int = 0

    @abstractmethod
    def update(self, dt: float) -> None:
        """Advance the model by one time step."""
        ...

    def reset(self) -> None:
        """Reset the model to initial state."""
        self._tick = 0

    def get_state(self) -> Dict[str, Any]:
        """Return current state of the model."""
        return {"tick": self._tick}

    def get_stats(self) -> Dict[str, Any]:
        """Return statistics about the model."""
        return {"type": type(self).__name__, "name": self.config.name}
