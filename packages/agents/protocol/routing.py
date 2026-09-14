# Copyright (c) Ultrone Contributors. All rights reserved.
"""Agent message router and inbox dispatch."""

from __future__ import annotations

import logging
from typing import Callable, Dict, List, Optional

from .message import AgentMessage

logger = logging.getLogger("Ultrone.Protocol.Router")


class ProtocolRouter:
    """Routes messages between agents and manages recipient inboxes."""

    def __init__(self) -> None:
        self._inboxes: Dict[str, List[AgentMessage]] = {}
        self._handlers: Dict[str, Callable[[AgentMessage], Optional[AgentMessage]]] = {}

    def register_agent(
        self,
        agent_id: str,
        handler: Optional[Callable[[AgentMessage], Optional[AgentMessage]]] = None,
    ) -> None:
        """Register an agent mailbox and optional immediate callback handler."""
        if agent_id not in self._inboxes:
            self._inboxes[agent_id] = []
        if handler:
            self._handlers[agent_id] = handler

    def send(self, message: AgentMessage) -> Optional[AgentMessage]:
        """Send message to recipient agent."""
        recipient = message.recipient
        if recipient not in self._inboxes:
            self._inboxes[recipient] = []

        self._inboxes[recipient].append(message)
        logger.debug("Message %s routed from %s to %s", message.message_id, message.sender, recipient)

        # If synchronous handler is registered, invoke it
        if recipient in self._handlers:
            try:
                return self._handlers[recipient](message)
            except Exception as e:
                logger.error("Handler error delivering message to %s: %s", recipient, e)

        return None

    def poll_inbox(self, agent_id: str) -> List[AgentMessage]:
        """Retrieve and clear queued messages for an agent."""
        messages = self._inboxes.get(agent_id, [])
        self._inboxes[agent_id] = []
        return messages
