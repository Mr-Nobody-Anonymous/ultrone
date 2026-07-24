# Copyright (c) Ultrone Contributors. All rights reserved.
"""Abstract base agent with state machine, communications, and sensors."""

from __future__ import annotations

import logging
import uuid
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any, Callable
from enum import Enum
from dataclasses import dataclass

from data.entities import Unit, AgentState, DomainType, Contact
from comms.protocol import Message, MessageType, Priority

logger = logging.getLogger("Ultrone.Agents.Base")


class AgentCapability(Enum):
    """Capabilities an agent can have."""
    SENSE = "sense"
    MOVE = "move"
    ENGAGE = "engage"
    COMMUNICATE = "communicate"
    EVOLVE = "evolve"
    STEALTH = "stealth"
    RECON = "recon"


class BaseAgent:
    """
    Abstract base class for all military agents.
    
    Provides:
    - State machine (standby, active, engaged, returning, offline)
    - Communication interface
    - Sensor range management
    - Mission execution framework
    """

    def __init__(
        self,
        unit_id: str,
        domain: DomainType,
        unit_type: str,
        position: tuple,
        team: str = "blue",
        capabilities: List[AgentCapability] = None,
        message_bus: Optional[Any] = None,
    ):
        self.unit = Unit(
            unit_id=unit_id,
            domain=domain,
            unit_type=unit_type,
            position=position,
            team=team,
        )
        self.capabilities = capabilities or [
            AgentCapability.SENSE, AgentCapability.MOVE, AgentCapability.ENGAGE,
        ]
        self.state_history: List[str] = []
        self.message_handlers: Dict[MessageType, Callable] = {}
        self._sensor_callbacks: List[Callable] = []
        
        # Message bus for async pub/sub communications
        self.message_bus = message_bus

    @property
    def state(self) -> AgentState:
        return self.unit.state

    @state.setter
    def state(self, new_state: AgentState) -> None:
        old_state = self.unit.state
        self.unit.state = new_state
        self.state_history.append(f"{old_state.value}->{new_state.value}")
        # Publish state change on message bus
        if self.message_bus:
            self._publish_state_change(old_state, new_state)

    async def _publish_state_change(self, old_state: AgentState, new_state: AgentState) -> None:
        """Publish state transition to message bus."""
        if not self.message_bus:
            return
        message = Message.create(
            message_type=MessageType.STATUS,
            sender_id=self.unit.unit_id,
            content={
                "old_state": old_state.value,
                "new_state": new_state.value,
                "unit_type": self.unit.unit_type,
            },
            priority=Priority.ROUTINE,
        )
        await self.message_bus.publish(message)

    def can_perform(self, capability: AgentCapability) -> bool:
        """Check if agent has a capability and is operational."""
        return capability in self.capabilities and self.unit.is_operational()

    def set_position(self, x: float, y: float, z: float) -> None:
        """Update agent position."""
        self.unit.position = (x, y, z)

    def take_damage(self, damage: float) -> bool:
        """Apply damage. Returns True if destroyed."""
        result = self.unit.take_damage(damage)
        # Publish damage event on message bus
        if self.message_bus and result:
            self._publish_damage(damage)
        return result

    async def _publish_damage(self, damage: float) -> None:
        """Publish damage event to message bus."""
        if not self.message_bus:
            return
        message = Message.create(
            message_type=MessageType.DAMAGE,
            sender_id=self.unit.unit_id,
            content={"damage": damage, "health": self.unit.health},
            priority=Priority.IMMEDIATE,
        )
        await self.message_bus.publish(message)

    async def detect_target(self, contact: Contact) -> None:
        """Called when agent detects a target - publishes to message bus."""
        if not self.message_bus:
            return
        message = Message.create(
            message_type=MessageType.CONTACT_REPORT,
            sender_id=self.unit.unit_id,
            content={
                "contact_id": contact.contact_id,
                "domain": contact.domain.value,
                "position": contact.position,
                "threat_level": contact.threat_level.value if hasattr(contact.threat_level, 'value') else str(contact.threat_level),
            },
            priority=Priority.PRIORITY,
        )
        await self.message_bus.publish(message)

    async def report_engagement(self, contact_id: str, success: bool) -> None:
        """Called when agent engages a target - publishes to message bus."""
        if not self.message_bus:
            return
        message = Message.create(
            message_type=MessageType.HIT if success else MessageType.MISS,
            sender_id=self.unit.unit_id,
            content={"contact_id": contact_id, "success": success},
            priority=Priority.IMMEDIATE,
        )
        await self.message_bus.publish(message)

    def add_sensor_callback(self, callback: Callable) -> None:
        """Register callback for sensor detections."""
        self._sensor_callbacks.append(callback)

    def notify_sensors(self, contact: Contact) -> None:
        """Notify all registered callbacks of a contact."""
        for cb in self._sensor_callbacks:
            try:
                cb(contact)
            except Exception as e:
                logger.error(f"Sensor callback error: {e}")

    def create_message(
        self,
        message_type: MessageType,
        content: Dict[str, Any] = None,
        recipient: str = None,
        priority: Priority = Priority.ROUTINE,
    ) -> Message:
        """Create a message from this agent."""
        return Message.create(
            message_type=message_type,
            sender_id=self.unit.unit_id,
            content=content or {},
            recipient_id=recipient,
            priority=priority,
        )

    def handle_message(self, message: Message) -> Optional[Message]:
        """Process incoming message. Override for custom behavior."""
        handler = self.message_handlers.get(message.message_type)
        if handler:
            return handler(message)
        return None

    # Default state transitions
    def go_standby(self) -> None:
        """Transition to standby state."""
        if self.state != AgentState.STANDBY:
            self.state = AgentState.STANDBY

    def go_active(self) -> None:
        """Transition to active state."""
        self.state = AgentState.ACTIVE

    def go_engaged(self) -> None:
        """Transition to engaged state."""
        self.state = AgentState.ENGAGED

    def go_returning(self) -> None:
        """Transition to returning state."""
        self.state = AgentState.RETURNING

    def go_offline(self) -> None:
        """Transition to offline state."""
        self.state = AgentState.OFFLINE

    def is_operational(self) -> bool:
        """Check if agent can perform missions."""
        return self.unit.is_operational()

    def get_sensor_range(self) -> float:
        """Get maximum sensor range."""
        return self.unit.sensor_range

    def to_dict(self) -> dict:
        return self.unit.to_dict()

    @abstractmethod
    def take_turn(self, world_state: Any, messages: List[Message]) -> List[Message]:
        """
        Execute one turn of the agent.
        
        Override in subclasses to implement domain-specific behavior.
        """
        pass

    @abstractmethod
    def execute_mission(self, mission: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a mission order.
        
        Returns result dict with success status.
        """
        pass