# Copyright (c) Ultrone Contributors. All rights reserved.
"""Async pub/sub message bus for battlefield communications."""

import asyncio
import logging
from collections import defaultdict
from typing import Dict, List, Callable, Optional, Any
from dataclasses import dataclass, field
import uuid

from .protocol import Message, MessageType, Priority

logger = logging.getLogger("Ultrone.Comms.MessageBus")


@dataclass
class Subscription:
    """Subscriber callback with filter."""
    callback: Callable[[Message], Any]
    message_types: List[MessageType] = field(default_factory=list)
    priority_filter: Optional[Priority] = None


class MessageBus:
    """
    Asynchronous publish/subscribe message bus.
    
    Features:
    - Priority queue ordering (higher priority messages delivered first)
    - Message history for acknowledgment and replay
    - Broadcast and point-to-point messaging
    - Subscription filtering by message type and priority
    """
    
    def __init__(self, max_history: int = 1000):
        self.max_history = max_history
        self.subscribers: Dict[str, List[Subscription]] = defaultdict(list)
        self.message_history: List[Message] = []
        self._queue: asyncio.PriorityQueue = asyncio.PriorityQueue()
        self._running = False
        self._processing_task: Optional[asyncio.Task] = None
    
    async def start(self) -> None:
        """Start the message processing loop."""
        if not self._running:
            self._running = True
            self._processing_task = asyncio.create_task(self._process_queue())
            logger.info("MessageBus started")
    
    async def stop(self) -> None:
        """Stop the message processing loop."""
        self._running = False
        if self._processing_task:
            self._processing_task.cancel()
            try:
                await self._processing_task
            except asyncio.CancelledError:
                pass
        logger.info("MessageBus stopped")
    
    async def publish(self, message: Message) -> None:
        """Publish a message to the bus."""
        # Priority queue uses negative priority (higher priority = smaller number = processed first)
        priority_value = 4 - message.priority.value  # Invert: ROUTINE=4, CRITICAL=0
        await self._queue.put((priority_value, message))
        
        # Store in history
        self.message_history.append(message)
        if len(self.message_history) > self.max_history:
            self.message_history = self.message_history[-self.max_history:]
        
        logger.debug(f"Published message {message.message_id} type={message.message_type.value}")
    
    async def _process_queue(self) -> None:
        """Process messages from queue."""
        while self._running:
            try:
                priority_value, message = await self._queue.get()
                await self._deliver_message(message)
                self._queue.task_done()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error processing message: {e}")
    
    async def _deliver_message(self, message: Message) -> None:
        """Deliver message to all matching subscribers."""
        # Broadcast to all subscribers (None key)
        if None in self.subscribers:
            for sub in self.subscribers[None]:
                if self._matches_filter(sub, message):
                    try:
                        if asyncio.iscoroutinefunction(sub.callback):
                            await sub.callback(message)
                        else:
                            sub.callback(message)
                    except Exception as e:
                        logger.error(f"Subscriber error: {e}")
        
        # Deliver to recipient-specific subscribers
        if message.recipient_id:
            if message.recipient_id in self.subscribers:
                for sub in self.subscribers[message.recipient_id]:
                    if self._matches_filter(sub, message):
                        try:
                            if asyncio.iscoroutinefunction(sub.callback):
                                await sub.callback(message)
                            else:
                                sub.callback(message)
                        except Exception as e:
                            logger.error(f"Subscriber error: {e}")
            
            # Also deliver to wildcard subscribers
            if "*" in self.subscribers:
                for sub in self.subscribers["*"]:
                    if self._matches_filter(sub, message):
                        try:
                            if asyncio.iscoroutinefunction(sub.callback):
                                await sub.callback(message)
                            else:
                                sub.callback(message)
                        except Exception as e:
                            logger.error(f"Subscriber error: {e}")
    
    def _matches_filter(self, sub: Subscription, message: Message) -> bool:
        """Check if message matches subscription filter."""
        if sub.message_types and message.message_type not in sub.message_types:
            return False
        if sub.priority_filter and message.priority.value < sub.priority_filter.value:
            return False
        return True
    
    def subscribe(
        self,
        subscriber_id: str,
        callback: Callable[[Message], Any],
        message_types: List[MessageType] = None,
        priority_filter: Priority = None,
    ) -> None:
        """Subscribe to messages."""
        subscription = Subscription(
            callback=callback,
            message_types=message_types or [],
            priority_filter=priority_filter,
        )
        self.subscribers[subscriber_id].append(subscription)
        logger.debug(f"Subscribed {subscriber_id} to message bus")
    
    def unsubscribe(self, subscriber_id: str) -> None:
        """Remove a subscriber."""
        if subscriber_id in self.subscribers:
            del self.subscribers[subscriber_id]
            logger.debug(f"Unsubscribed {subscriber_id}")
    
    def get_history(self, message_type: MessageType = None, limit: int = 100) -> List[Message]:
        """Get message history, optionally filtered."""
        if message_type:
            return [m for m in self.message_history if m.message_type == message_type][-limit:]
        return self.message_history[-limit:]
    
    def get_stats(self) -> dict:
        """Get message bus statistics."""
        return {
            "queue_size": self._queue.qsize(),
            "history_size": len(self.message_history),
            "subscriber_count": len(self.subscribers),
            "running": self._running,
        }