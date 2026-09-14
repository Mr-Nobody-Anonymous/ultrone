# Copyright (c) Ultrone Contributors. All rights reserved.
"""Agent-to-Agent standard protocol message contract."""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class ProtocolMessageType(str, Enum):
    """Standard message types for inter-agent communication."""

    REQUEST = "REQUEST"
    INFORM = "INFORM"
    PROPOSE = "PROPOSE"
    ACCEPT = "ACCEPT"
    REJECT = "REJECT"
    HANDOFF = "HANDOFF"
    DELEGATE = "DELEGATE"
    QUERY = "QUERY"
    FAILURE = "FAILURE"


@dataclass
class AgentMessage:
    """Universal standard message contract for multi-agent coordination."""

    sender: str
    recipient: str
    message_type: ProtocolMessageType = ProtocolMessageType.INFORM
    conversation_id: str = field(default_factory=lambda: f"conv-{uuid.uuid4().hex[:8]}")
    task_id: str = field(default_factory=lambda: f"task-{uuid.uuid4().hex[:8]}")
    priority: int = 1  # 0=low, 1=routine, 2=high, 3=emergency
    payload: Dict[str, Any] = field(default_factory=dict)
    capabilities_required: List[str] = field(default_factory=list)
    deadline: Optional[float] = None
    correlation_id: Optional[str] = None
    signature: Optional[str] = None
    timestamp: float = field(default_factory=time.time)
    message_id: str = field(default_factory=lambda: f"msg-{uuid.uuid4().hex[:8]}")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "message_id": self.message_id,
            "sender": self.sender,
            "recipient": self.recipient,
            "message_type": self.message_type.value,
            "conversation_id": self.conversation_id,
            "task_id": self.task_id,
            "priority": self.priority,
            "payload": self.payload,
            "capabilities_required": self.capabilities_required,
            "deadline": self.deadline,
            "correlation_id": self.correlation_id,
            "signature": self.signature,
            "timestamp": self.timestamp,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> AgentMessage:
        return cls(
            message_id=data.get("message_id", f"msg-{uuid.uuid4().hex[:8]}"),
            sender=data["sender"],
            recipient=data["recipient"],
            message_type=ProtocolMessageType(data.get("message_type", "INFORM")),
            conversation_id=data.get("conversation_id", ""),
            task_id=data.get("task_id", ""),
            priority=data.get("priority", 1),
            payload=data.get("payload", {}),
            capabilities_required=data.get("capabilities_required", []),
            deadline=data.get("deadline"),
            correlation_id=data.get("correlation_id"),
            signature=data.get("signature"),
            timestamp=data.get("timestamp", time.time()),
        )
