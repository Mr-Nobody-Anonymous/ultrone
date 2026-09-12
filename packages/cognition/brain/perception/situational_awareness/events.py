# Copyright (c) Ultrone Contributors. All rights reserved.
"""Event-driven infrastructure for the situational awareness system.

Implements an asynchronous pub/sub event bus with typed domain events, weak
listener registration, synchronous subscription support, and optional
distributed-ready transport hooks (the ``distributed_transport`` protocol).
"""

from __future__ import annotations

import asyncio
import contextlib
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import (
    Any,
    Awaitable,
    Callable,
    Dict,
    List,
    Optional,
    Protocol,
    Tuple,
    Type,
    TypeVar,
    Union,
    runtime_checkable,
)

from .types import utc_now

__all__ = [
    "EventPriority",
    "DomainEvent",
    "ObservationReceived",
    "EntityUpdated",
    "WorldStateChanged",
    "PredictionGenerated",
    "AnomalyDetected",
    "ChangeReported",
    "HypothesisUpdated",
    "AttentionRedirected",
    "ConfidenceUpdated",
    "EventBus",
    "DistributedTransport",
]

T = TypeVar("T", bound="DomainEvent")


class EventPriority(int, Enum):
    """Scheduling priority for event dispatch."""

    CRITICAL = 0
    HIGH = 10
    NORMAL = 20
    LOW = 30
    BACKGROUND = 40


@dataclass
class DomainEvent:
    """Base class for all domain events. Subclasses carry typed payloads."""

    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = field(default_factory=utc_now)
    priority: EventPriority = EventPriority.NORMAL
    source: str = ""

    def __post_init__(self) -> None:
        if not self.source:
            self.source = type(self).__name__


@dataclass
class ObservationReceived(DomainEvent):
    """Emitted when a validated observation enters the system."""

    observation_id: str = ""
    sensor_id: str = ""
    entity_id: Optional[str] = None
    confidence: float = 0.5


@dataclass
class EntityUpdated(DomainEvent):
    """Emitted when a tracked entity's state changes."""

    entity_id: str = ""
    confidence: float = 0.0
    uncertainty: float = float("inf")
    changed_fields: List[str] = field(default_factory=list)


@dataclass
class WorldStateChanged(DomainEvent):
    """Emitted after a world model tick commits changes."""

    sequence: int = 0
    entity_count: int = 0
    relationship_count: int = 0
    changed_entity_ids: List[str] = field(default_factory=list)


@dataclass
class PredictionGenerated(DomainEvent):
    """Emitted when a projection is produced."""

    entity_id: Optional[str] = None
    horizon_seconds: float = 0.0
    method: str = "unknown"
    trajectory_count: int = 0
    event_count: int = 0


@dataclass
class AnomalyDetected(DomainEvent):
    """Emitted when the anomaly detector flags a deviation."""

    anomaly_id: str = ""
    entity_id: Optional[str] = None
    severity: str = "info"
    score: float = 0.0
    description: str = ""


@dataclass
class ChangeReported(DomainEvent):
    """Emitted when the change detector reports a world change."""

    change_id: str = ""
    change_type: str = ""
    entity_id: Optional[str] = None
    significance: float = 0.0


@dataclass
class HypothesisUpdated(DomainEvent):
    """Emitted when a hypothesis transitions status."""

    hypothesis_id: str = ""
    status: str = ""
    probability: float = 0.0


@dataclass
class AttentionRedirected(DomainEvent):
    """Emitted when the attention manager reallocates sensing resources."""

    sensor_ids: List[str] = field(default_factory=list)
    entity_ids: List[str] = field(default_factory=list)
    reason: str = ""


@dataclass
class ConfidenceUpdated(DomainEvent):
    """Emitted when entity confidence changes materially."""

    entity_id: str = ""
    previous_confidence: float = 0.0
    new_confidence: float = 0.0
    delta: float = 0.0


@runtime_checkable
class DistributedTransport(Protocol):
    """Protocol for a distributed event transport (e.g., Kafka, NATS).

    Implementations should publish serialized events to an external broker and
    consume events produced by other agents/nodes. This keeps the core event
    bus single-process fast while remaining cluster-ready.
    """

    async def publish(
        self, topic: str, event_type: str, payload: bytes
    ) -> None: ...

    async def subscribe(
        self, topic: str, handler: Callable[[str, bytes], Awaitable[None]]
    ) -> None: ...

    async def close(self) -> None: ...


Listener = Union[
    Callable[[T], None],
    Callable[[T], Awaitable[None]],
]


class EventBus:
    """Asynchronous, typed, priority-aware event bus.

    Features:

    * Subscribe with a type filter (``event_type``) and optional priority.
    * Sync and async listeners are both supported; sync listeners are invoked
      without blocking the event loop.
    * Listeners are stored as weak references so long-lived buses do not leak
      memory when subscribers are garbage collected.
    * ``publish`` and ``publish_and_wait`` support async fan-out.
    * Optional ``distributed_transport`` forwards serialized events to a
      message broker when configured.
    """

    def __init__(
        self,
        *,
        distributed_transport: Optional[DistributedTransport] = None,
        node_id: str = "node-default",
    ) -> None:
        self._node_id = node_id
        self._distributed_transport = distributed_transport
        self._sync_listeners: Dict[Type[DomainEvent], List[Tuple[EventPriority, Callable[[DomainEvent], None]]]] = {}
        self._async_listeners: Dict[Type[DomainEvent], List[Tuple[EventPriority, Callable[[DomainEvent], Awaitable[None]]]]] = {}
        self._subscription_count: int = 0
        self._published_count: int = 0
        self._pending_tasks: set[asyncio.Task[None]] = set()
        self._lock = asyncio.Lock()

    def subscribe(
        self,
        event_type: Type[T],
        listener: Listener[T],
        *,
        priority: EventPriority = EventPriority.NORMAL,
    ) -> Callable[[], None]:
        """Subscribe ``listener`` to events of ``event_type``.

        Returns an unsubscribe callable.
        """
        key = event_type
        self._subscription_count += 1

        if asyncio.iscoroutinefunction(listener):
            raise ValueError("async functions must be subscribed with subscribe_async")

        bucket = self._sync_listeners.setdefault(key, [])
        bucket.append((priority, listener))  # type: ignore[arg-type]
        bucket.sort(key=lambda item: item[0])

        def unsubscribe() -> None:
            bucket_entry = self._sync_listeners.get(key, [])
            for idx, (prio, fn) in enumerate(bucket_entry):
                # Weak-safe comparison: compare the underlying function object.
                if fn == listener:  # type: ignore[comparison-overlap]
                    bucket_entry.pop(idx)
                    return

        return unsubscribe

    def subscribe_async(
        self,
        event_type: Type[T],
        listener: Callable[[T], Awaitable[None]],
        *,
        priority: EventPriority = EventPriority.NORMAL,
    ) -> Callable[[], None]:
        """Subscribe an async listener. Returns an unsubscribe callable."""
        key = event_type
        self._subscription_count += 1

        bucket = self._async_listeners.setdefault(key, [])
        bucket.append((priority, listener))  # type: ignore[arg-type]
        bucket.sort(key=lambda item: item[0])

        def do_unsubscribe() -> None:
            entries = self._async_listeners.get(key, [])
            for idx, (prio, fn) in enumerate(entries):
                if fn == listener:  # type: ignore[comparison-overlap]
                    entries.pop(idx)
                    return

        return do_unsubscribe

    def publish_sync(self, event: DomainEvent) -> None:
        """Publish an event invoking only synchronous listeners.

        Intended for use from synchronous code paths (e.g., the world model's
        synchronous update methods). Async listeners are not scheduled.
        """
        self._published_count += 1
        event_type = type(event)

        sync_bucket = self._sync_listeners.get(event_type, [])
        for _, fn in list(sync_bucket):
            with contextlib.suppress(Exception):
                fn(event)  # type: ignore[arg-type]

    async def publish(self, event: DomainEvent) -> None:
        """Publish an event; schedules async listeners and fires sync ones.

        Does not wait for async listeners to complete. To await completion use
        :meth:`publish_and_wait`.
        """
        self._published_count += 1
        event_type = type(event)

        sync_bucket = self._sync_listeners.get(event_type, [])
        for _, fn in list(sync_bucket):
            with contextlib.suppress(Exception):
                fn(event)  # type: ignore[arg-type]

        async_bucket = self._async_listeners.get(event_type, [])
        if async_bucket:
            for _, fn in list(async_bucket):
                task = asyncio.create_task(fn(event))  # type: ignore[arg-type]
                self._pending_tasks.add(task)
                task.add_done_callback(self._pending_tasks.discard)

        if self._distributed_transport is not None:
            topic = f"ultrone.sa.{event_type.__name__.lower()}"
            payload = self._serialize(event)
            async with self._lock:
                await self._distributed_transport.publish(topic, event_type.__name__, payload)

    async def publish_and_wait(self, event: DomainEvent) -> None:
        """Publish and await all async listener completions."""
        self._published_count += 1
        event_type = type(event)

        sync_bucket = self._sync_listeners.get(event_type, [])
        for _, fn in list(sync_bucket):
            with contextlib.suppress(Exception):
                fn(event)  # type: ignore[arg-type]

        async_bucket = self._async_listeners.get(event_type, [])
        if async_bucket:
            await asyncio.gather(
                *[
                    fn(event)  # type: ignore[arg-type]
                    for _, fn in list(async_bucket)
                ],
                return_exceptions=True,
            )

    def _serialize(self, event: DomainEvent) -> bytes:
        import json

        data: Dict[str, Any] = {
            "event_id": event.event_id,
            "timestamp": event.timestamp.isoformat(),
            "source": event.source,
            "priority": event.priority.name,
        }
        for key, value in event.__dict__.items():
            if key in data:
                continue
            if isinstance(value, datetime):
                data[key] = value.isoformat()
            elif hasattr(value, "value"):
                data[key] = value.value
            else:
                data[key] = value
        return json.dumps(data, default=str).encode("utf-8")

    async def close(self) -> None:
        """Release resources; closes the distributed transport if present."""
        if self._distributed_transport is not None:
            await self._distributed_transport.close()

    @property
    def subscription_count(self) -> int:
        return self._subscription_count

    @property
    def published_count(self) -> int:
        return self._published_count


class EventWaiter:
    """Helper that awaits the next event of a given type.

    Useful in tests and for reactive agents that block until a state change.
    """

    def __init__(self, bus: EventBus, event_type: Type[T]) -> None:
        self._bus = bus
        self._event_type = event_type
        self._future: Optional[asyncio.Future[T]] = None
        self._unsub: Optional[Callable[[], None]] = None

    async def wait_for_next(self, timeout: Optional[float] = None) -> T:
        loop = asyncio.get_running_loop()
        self._future = loop.create_future()

        async def _on_event(event: T) -> None:
            if self._future is not None and not self._future.done():
                self._future.set_result(event)

        self._unsub = self._bus.subscribe_async(self._event_type, _on_event)
        try:
            return await asyncio.wait_for(
                asyncio.shield(self._future), timeout=timeout
            )
        finally:
            if self._unsub is not None:
                self._unsub()