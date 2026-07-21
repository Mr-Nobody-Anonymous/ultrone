# Copyright (c) Ultrone Contributors. All rights reserved.
"""Abstract base agent with state machine, communications, and sensors."""

import logging
import uuid
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any, Callable
from enum import Enum
from dataclasses import dataclass

from ...data.entities import Unit, AgentState, DomainType, Contact
from ...comms.protocol import Message, MessageType, Priority

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
    
    @property
    def state(self) -> AgentState:
        return self.unit.state
    
    @state.setter
    def state(self, new_state: AgentState) -> None:
        old_state = self.unit.state
        self.unit.state = new_state
        self.state_history.append(f"{old_state.value}->{new_state.value}")
    
    def can_perform(self, capability: AgentCapability) -> bool:
        """Check if agent has a capability and is operational."""
        return capability in self.capabilities and self.unit.is_operational()
    
    def set_position(self, x: float, y: float, z: float) -> None:
        """Update agent position."""
        self.unit.position = (x, y, z)
    
    def take_damage(self, damage: float) -> bool:
        """Apply damage. Returns True if destroyed."""
        return self.unit.take_damage(damage)
    
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