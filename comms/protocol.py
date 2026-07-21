# Copyright (c) Ultrone Contributors. All rights reserved.
"""Military communication protocol definitions."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, Any, Optional
import uuid


class Priority(Enum):
    """Message priority levels (MIL-STD-1591 style)."""
    ROUTINE = 0      # Routine messages
    PRIORITY = 1     # Priority messages
    IMMEDIATE = 2    # Immediate priority
    FLASH = 3        # Flash priority (critical tactical)
    CRITICAL = 4     # Critical/Emergency


class MessageType(Enum):
    """Military message types for C2 communications."""
    # Intelligence
    CONTACT_REPORT = "CONTACT_REPORT"      # Spot report of enemy/friend
    SPOT_REPORT = "SPOT_REPORT"            # Detailed spot report
    SIGINT = "SIGINT"                      # Signals intelligence
    IMINT = "IMINT"                        # Image intelligence
    HUMINT = "HUMINT"                      # Human intelligence
    
    # Orders and Commands
    ORDERS = "ORDERS"                     # Tactical orders
    MISSION = "MISSION"                    # Mission assignment
    TASKING = "TASKING"                   # Task assignment
    EXECUTION = "EXECUTION"               # Execution confirmation
    
    # Status
    STATUS = "STATUS"                      # Asset status report
    HEALTH = "HEALTH"                     # System health
    POSITION = "POSITION"                 # Position report
    FUEL = "FUEL"                        # Fuel status
    AMMUNITION = "AMMUNITION"            # Ammo status
    
    # Engagement
    ENGAGEMENT = "ENGAGEMENT"             # Weapon engagement
    HIT = "HIT"                          # Target hit
    MISS = "MISS"                        # Target missed
    DAMAGE = "DAMAGE"                    # Taking damage
    
    # Movement
    MOVEMENT = "MOVEMENT"                 # Movement orders
    RTB = "RTB"                          # Return to base
    
    # Mission Management
    MISSION_START = "MISSION_START"
    MISSION_COMPLETE = "MISSION_COMPLETE"
    MISSION_FAILED = "MISSION_FAILED"
    
    # Evolution commands
    EVOLVE_COMMAND = "EVOLVE_COMMAND"
    GENOME_UPDATE = "GENOME_UPDATE"
    
    # Generic
    ACKNOWLEDGE = "ACKNOWLEDGE"
    NACK = "NACK"
    QUERY = "QUERY"
    RESPONSE = "RESPONSE"


@dataclass
class Message:
    """Military-style message with classification and provenance."""
    message_id: str
    message_type: MessageType
    sender_id: str
    recipient_id: Optional[str]
    priority: Priority = Priority.ROUTINE
    content: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    classification: str = "UNCLASS"  # UNCLASS, CONFIDENTIAL, SECRET, etc.
    ack_requested: bool = False
    correlation_id: Optional[str] = None
    
    def __post_init__(self):
        if not self.correlation_id:
            self.correlation_id = self.message_id
    
    def to_dict(self) -> dict:
        return {
            "message_id": self.message_id,
            "message_type": self.message_type.value,
            "sender_id": self.sender_id,
            "recipient_id": self.recipient_id,
            "priority": self.priority.name,
            "timestamp": self.timestamp,
            "classification": self.classification,
            "ack_requested": self.ack_requested,
            "correlation_id": self.correlation_id,
            "content": self.content,
        }
    
    @classmethod
    def create(
        cls,
        message_type: MessageType,
        sender_id: str,
        content: Dict[str, Any] = None,
        recipient_id: str = None,
        priority: Priority = Priority.ROUTINE,
        classification: str = "UNCLASS",
    ) -> 'Message':
        """Factory method to create a message."""
        return cls(
            message_id=f"MSG-{uuid.uuid4().hex[:8].upper()}",
            message_type=message_type,
            sender_id=sender_id,
            recipient_id=recipient_id,
            priority=priority,
            content=content or {},
            classification=classification,
        )