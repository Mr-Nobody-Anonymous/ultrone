# Copyright (c) Ultrone Contributors. All rights reserved.
"""Base interface for all coordination algorithms."""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger("Ultrone.Brain.Reasoning.Coordination.Base")


@dataclass
class CoordinationConfig:
    """Base configuration for coordination algorithms."""
    num_agents: int = 2
    communication_delay: float = 0.0
    timeout_ms: float = 1000.0


@dataclass
class CoordinationMessage:
    """A message exchanged during coordination."""
    sender_id: str
    receiver_id: Optional[str] = None
    content: Dict[str, Any] = field(default_factory=dict)
    msg_type: str = "inform"


class BaseCoordinator(ABC):
    """Abstract interface for coordination algorithms."""

    def __init__(self, config: CoordinationConfig):
        self.config = config
        self._agents: Dict[str, Any] = {}

    def register_agent(self, agent_id: str, agent: Any) -> None:
        self._agents[agent_id] = agent

    @abstractmethod
    def coordinate(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Run one coordination cycle."""
        ...

    @abstractmethod
    def get_stats(self) -> Dict[str, Any]:
        ...