# Copyright (c) Ultrone Contributors. All rights reserved.
"""McpTelemetryStreamer: High-rate Asynchronous Streaming and SSE Telemetry for MCP."""

from __future__ import annotations

import collections
import json
import logging
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Set

logger = logging.getLogger("Ultrone.MCP.Streaming")


@dataclass
class TelemetryFrame:
    """A discrete streaming telemetry frame."""

    channel: str
    sequence_id: int
    timestamp: float
    payload: Dict[str, Any]

    def to_sse(self) -> str:
        """Format frame as a standard Server-Sent Event (SSE) block."""
        data_str = json.dumps(self.payload)
        return f"event: {self.channel}\nid: {self.sequence_id}\ndata: {data_str}\n\n"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "channel": self.channel,
            "sequence_id": self.sequence_id,
            "timestamp": self.timestamp,
            "data": self.payload,
        }


class McpTelemetryStreamer:
    """Asynchronous pub/sub streaming transport for high-frequency MCP feeds."""

    def __init__(self, ring_buffer_size: int = 100) -> None:
        self.ring_buffer_size = ring_buffer_size
        self._channels: Dict[str, collections.deque[TelemetryFrame]] = {}
        self._subscribers: Dict[str, Dict[str, Callable[[TelemetryFrame], None]]] = {}
        self._sequence_counters: Dict[str, int] = {}
        self._lock = threading.RLock()

    def register_channel(self, channel: str) -> None:
        """Create a new streaming channel (e.g. 'telemetry/radar', 'telemetry/gps')."""
        with self._lock:
            if channel not in self._channels:
                self._channels[channel] = collections.deque(maxlen=self.ring_buffer_size)
                self._subscribers[channel] = {}
                self._sequence_counters[channel] = 0
                logger.debug("Registered MCP streaming channel '%s'", channel)

    def subscribe(self, channel: str, subscriber_id: str, callback: Callable[[TelemetryFrame], None]) -> bool:
        """Subscribe a callback to a high-frequency channel."""
        with self._lock:
            self.register_channel(channel)
            self._subscribers[channel][subscriber_id] = callback
            logger.debug("Subscriber '%s' subscribed to channel '%s'", subscriber_id, channel)
            return True

    def unsubscribe(self, channel: str, subscriber_id: str) -> bool:
        """Remove a subscriber from a channel."""
        with self._lock:
            if channel in self._subscribers and subscriber_id in self._subscribers[channel]:
                del self._subscribers[channel][subscriber_id]
                return True
            return False

    def publish(self, channel: str, payload: Dict[str, Any]) -> TelemetryFrame:
        """Publish a telemetry payload to all channel subscribers without request-response RPC overhead."""
        with self._lock:
            self.register_channel(channel)
            seq = self._sequence_counters[channel] + 1
            self._sequence_counters[channel] = seq

            frame = TelemetryFrame(
                channel=channel,
                sequence_id=seq,
                timestamp=time.time(),
                payload=payload,
            )
            self._channels[channel].append(frame)

            # Distribute to active subscribers
            for sub_id, cb in list(self._subscribers[channel].items()):
                try:
                    cb(frame)
                except Exception as exc:
                    logger.warning("Subscriber '%s' failed on frame %d: %s", sub_id, seq, exc)

            return frame

    def get_latest_frame(self, channel: str) -> Optional[TelemetryFrame]:
        """Fetch the most recent telemetry frame without blocking."""
        with self._lock:
            if channel in self._channels and len(self._channels[channel]) > 0:
                return self._channels[channel][-1]
            return None

    def get_history(self, channel: str, limit: int = 10) -> List[TelemetryFrame]:
        """Fetch the last N frames from the ring buffer."""
        with self._lock:
            if channel in self._channels:
                return list(self._channels[channel])[-limit:]
            return []
