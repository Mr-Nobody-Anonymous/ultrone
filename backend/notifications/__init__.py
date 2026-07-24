"""Notification manager — WebSocket push, email, webhooks, and in-app alerts."""

import os
import json
import time
import logging
import threading
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Any
from enum import Enum

logger = logging.getLogger("argus.notifications")


class NotificationChannel(Enum):
    WEBSOCKET = "websocket"
    EMAIL = "email"
    WEBHOOK = "webhook"
    SLACK = "slack"
    PUSH = "push"
    SMS = "sms"


class NotificationPriority(Enum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


@dataclass
class Notification:
    id: str
    title: str
    message: str
    channel: NotificationChannel = NotificationChannel.WEBSOCKET
    priority: NotificationPriority = NotificationPriority.NORMAL
    event_id: Optional[int] = None
    camera_id: Optional[int] = None
    user_id: Optional[int] = None
    metadata: Dict = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)
    read: bool = False


class NotificationManager:
    """Central notification dispatch with multi-channel support."""

    def __init__(self):
        self._channels: Dict[str, List[Callable]] = {}
        self._history: List[Notification] = []
        self._callbacks: Dict[NotificationChannel, List[Callable]] = {}
        self._lock = threading.RLock()
        self._max_history = 1000

    def register_channel(self, channel: NotificationChannel, handler: Callable) -> None:
        with self._lock:
            if channel not in self._callbacks:
                self._callbacks[channel] = []
            self._callbacks[channel].append(handler)

    def send(self, notification: Notification) -> bool:
        with self._lock:
            self._history.append(notification)
            if len(self._history) > self._max_history:
                self._history.pop(0)
            handlers = self._callbacks.get(notification.channel, [])
            for handler in handlers:
                try:
                    handler(notification)
                except Exception as e:
                    logger.error(f"Notification handler error: {e}")
            return len(handlers) > 0

    def notify_event(self, event) -> None:
        notification = Notification(
            id=f"evt_{event.id}_{int(time.time())}",
            title=event.title or event.event_type.value,
            message=event.description[:200] if event.description else "",
            channel=NotificationChannel.WEBSOCKET,
            priority=NotificationPriority.NORMAL,
            event_id=event.id,
            camera_id=event.camera_id,
            metadata={"severity": event.severity.value, "event_type": event.event_type.value},
        )
        self.send(notification)

    def get_history(self, limit: int = 50) -> List[Notification]:
        with self._lock:
            return sorted(self._history, key=lambda n: n.created_at, reverse=True)[:limit]

    def mark_read(self, notification_id: str) -> bool:
        with self._lock:
            for n in self._history:
                if n.id == notification_id:
                    n.read = True
                    return True
            return False

    def send_webhook(self, url: str, payload: Dict) -> bool:
        try:
            import requests
            resp = requests.post(url, json=payload, timeout=10)
            return resp.status_code < 500
        except Exception as e:
            logger.error(f"Webhook error: {e}")
            return False

    def send_email(self, to: str, subject: str, body: str) -> bool:
        try:
            import smtplib
            from email.mime.text import MIMEText
            msg = MIMEText(body)
            msg["Subject"] = subject
            msg["To"] = to
            msg["From"] = os.environ.get("SMTP_FROM", "argus@ultrone.ai")
            with smtplib.SMTP(os.environ.get("SMTP_HOST", "localhost"),
                              int(os.environ.get("SMTP_PORT", 587))) as server:
                server.starttls()
                server.login(os.environ.get("SMTP_USER", ""), os.environ.get("SMTP_PASS", ""))
                server.send_message(msg)
            return True
        except Exception as e:
            logger.error(f"Email error: {e}")
            return False
