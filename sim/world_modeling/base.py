"""Base classes for world modeling components."""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("Ultrone.Sim.WorldModeling.Base")


@dataclass
class WorldModelConfig:
    """Base configuration for world models."""
    enabled: bool = True
    update_interval: int = 1  # ticks between updates
    seed: int = 42


class WorldModel(ABC):
    """Abstract interface for world modeling components."""

    def __init__(self, config: WorldModelConfig):
        self.config = config
        self._tick = 0

    @abstractmethod
    def update(self, dt: float) -> None:
        """Advance the model by one time step."""
        ...

    @abstractmethod
    def get_state(self) -> Dict[str, Any]:
        """Return current model state for observation."""
        ...

    def reset(self) -> None:
        """Reset the model to initial state."""
        self._tick = 0

