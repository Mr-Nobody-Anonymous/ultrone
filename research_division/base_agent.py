# Copyright (c) Ultrone Contributors. All rights reserved.
"""Base agent for the ULTRONE Autonomous Research Division.

Research agents communicate via asynchronous events on the message bus,
use the knowledge engine for memory, and log every action for full
auditability and reproducibility.
"""

from __future__ import annotations

import logging
import time
from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, Dict, List, Optional

from comms.protocol import Message, MessageType, Priority
from knowledge_engine.memory_manager import KnowledgeMemoryManager
from research_db.store import ResearchDatabase

logger = logging.getLogger("Ultrone.ResearchDivision.Base")


class ResearchAgentRole(Enum):
    """Roles for research division agents."""

    SCOUT = "research_scout"
    ANALYZER = "paper_analyzer"
    EXTRACTOR = "algorithm_extractor"
    PLANNER = "implementation_planner"
    CODER = "code_generator"
    BENCHMARKER = "benchmark_agent"
    EXPERIMENTER = "experiment_manager"
    GRAPH_BUILDER = "knowledge_graph_builder"
    CITATION_MANAGER = "citation_manager"
    MEMORY_MANAGER = "memory_manager"
    REVIEWER = "quality_reviewer"
    SAFETY = "safety_validator"
    OPTIMIZER = "performance_optimizer"
    WRITER = "documentation_writer"
    RELEASER = "release_manager"
    COORDINATOR = "coordinator"


class ResearchAgent(ABC):
    """Base class for all research division agents.

    Features
    --------
    - Unique agent ID with role
    - Message bus integration (async publish/subscribe)
    - Knowledge engine access
    - Research database access
    - Full action logging
    """

    def __init__(
        self,
        agent_id: str,
        role: ResearchAgentRole,
        message_bus: Optional[Any] = None,
        knowledge: Optional[KnowledgeMemoryManager] = None,
        research_db: Optional[ResearchDatabase] = None,
        config: Optional[Dict[str, Any]] = None,
    ):
        self.agent_id = agent_id
        self.role = role
        self.message_bus = message_bus
        self.knowledge = knowledge or KnowledgeMemoryManager()
        self.research_db = research_db or ResearchDatabase()
        self.config = config or {}
        self.log: List[Dict[str, Any]] = []
        self.message_handlers: Dict[MessageType, Any] = {}
        self.created_at = time.time()
        self.actions_taken: int = 0

        if self.message_bus:
            self.message_bus.subscribe(agent_id, self.handle_message)

    # ------------------------------------------------------------------
    # Communication
    # ------------------------------------------------------------------
    async def publish(
        self,
        message_type: MessageType,
        content: Dict[str, Any],
        recipient_id: Optional[str] = None,
        priority: Priority = Priority.ROUTINE,
    ) -> None:
        """Publish a message to the bus."""
        if not self.message_bus:
            return
        message = Message.create(
            message_type=message_type,
            sender_id=self.agent_id,
            content=content,
            recipient_id=recipient_id,
            priority=priority,
        )
        await self.message_bus.publish(message)

    def handle_message(self, message: Message) -> None:
        """Handle an incoming message (sync wrapper)."""
        handler = self.message_handlers.get(message.message_type)
        if handler:
            try:
                result = handler(message)
                self._log_action(
                    "handle_message",
                    {"message_id": message.message_id, "type": message.message_type.value},
                    result,
                )
            except Exception as e:
                self._log_action("handle_message_error", {"error": str(e)}, None)

    # ------------------------------------------------------------------
    # Logging
    # ------------------------------------------------------------------
    def _log_action(self, action: str, details: Dict[str, Any] = None, result: Any = None) -> None:
        """Log every agent action with timestamp."""
        self.actions_taken += 1
        entry = {
            "timestamp": time.time(),
            "agent_id": self.agent_id,
            "role": self.role.value,
            "action": action,
            "details": details or {},
            "result": result if isinstance(result, (dict, list, str, int, float, bool, type(None))) else str(result),
        }
        self.log.append(entry)
        logger.debug("[%s] %s: %s", self.agent_id, action, details)

    def get_log(self) -> List[Dict[str, Any]]:
        """Return the agent's full action log."""
        return self.log

    def get_stats(self) -> Dict[str, Any]:
        """Return agent statistics."""
        return {
            "agent_id": self.agent_id,
            "role": self.role.value,
            "actions_taken": self.actions_taken,
            "log_entries": len(self.log),
            "uptime_seconds": time.time() - self.created_at,
        }

    # ------------------------------------------------------------------
    # Abstract interface
    # ------------------------------------------------------------------
    @abstractmethod
    async def run(self, *args: Any, **kwargs: Any) -> Dict[str, Any]:
        """Execute the agent's primary task.

        Must be implemented by each specialized agent.
        """
