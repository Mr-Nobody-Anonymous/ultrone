"""Base classes for AI architecture patterns."""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

logger = logging.getLogger("Ultrone.AIArchitectures.Base")


@dataclass
class AIArchitectureConfig:
    """Base configuration for AI architectures."""
    name: str = "base_architecture"
    debug: bool = False


class AIArchitecture(ABC):
    """Abstract interface for AI decision-making architectures."""

    def __init__(self, config: AIArchitectureConfig):
        self.config = config
        self._last_action: Optional[str] = None

    @abstractmethod
    def decide(self, state: Dict[str, Any]) -> str:
        """Select an action based on the current state."""
        ...

    @abstractmethod
    def reset(self) -> None:
        """Reset the architecture to initial state."""
        ...

    def get_stats(self) -> Dict[str, Any]:
        return {
            "type": type(self).__name__,
            "name": self.config.name,
            "last_action": self._last_action,
        }
