"""
REST API — FastAPI-based REST and WebSocket API with JWT auth, RBAC,
rate limiting, pagination, streaming, OpenAPI docs, and health endpoints.
"""

import os
import json
import time
import logging
import asyncio
from typing import Any, Callable, Dict, List, Optional, Tuple
from dataclasses import dataclass, field

logger = logging.getLogger("argus.api")


@dataclass
class APIResponse:
    success: bool = True
    data: Any = None
    error: Optional[str] = None
    message: str = ""
    pagination: Optional[Dict] = None
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict:
        result = {
            "success": self.success,
            "timestamp": self.timestamp,
        }
        if self.data is not None:
            result["data"] = self.data
        if self.error:
            result["error"] = self.error
        if self.message:
            result["message"] = self.message
        if self.pagination:
            result["pagination"] = self.pagination
        return result


@dataclass
class PaginationParams:
    page: int = 1
    per_page: int = 20
    max_per_page: int = 100

    def offset(self) -> int:
        return (self.page - 1) * self.per_page

    def to_dict(self, total: int) -> Dict:
        return {
            "page": self.page,
            "per_page": self.per_page,
            "total": total,
            "total_pages": max(1, (total + self.per_page - 1) // self.per_page),
        }


class APIException(Exception):
    def __init__(self, status_code: int, message: str, details: Optional[Dict] = None):
        self.status_code = status_code
        self.message = message
        self.details = details or {}


def api_response(success: bool = True, data: Any = None,
                 error: Optional[str] = None, message: str = "",
                 pagination: Optional[Dict] = None) -> Dict:
    return APIResponse(
        success=success, data=data, error=error,
        message=message, pagination=pagination,
    ).to_dict()


def paginated_response(data: List, total: int, params: PaginationParams) -> Dict:
    return api_response(
        data=data,
        pagination=params.to_dict(total),
    )


class RouterRegistry:
    """Registry of API routes for documentation generation."""

    def __init__(self):
        self._routes: List[Dict] = []

    def register(self, method: str, path: str, description: str,
                 auth_required: bool = True, permissions: Optional[List[str]] = None) -> None:
        self._routes.append({
            "method": method.upper(),
            "path": path,
            "description": description,
            "auth_required": auth_required,
            "permissions": permissions or [],
        })

    def get_routes(self) -> List[Dict]:
        return sorted(self._routes, key=lambda r: r["path"])


router_registry = RouterRegistry()


def register_route(method: str, path: str, description: str = "",
                   auth_required: bool = True, permissions: Optional[List[str]] = None):
    """Decorator to register API routes."""
    def decorator(func):
        router_registry.register(method, path, description or func.__doc__ or "",
                                 auth_required, permissions)
        return func
    return decorator


class WebSocketManager:
    """Manages WebSocket connections for real-time streaming."""

    def __init__(self):
        self._connections: Dict[str, set] = {}
        self._lock = asyncio.Lock()

    async def register(self, channel: str, websocket) -> None:
        async with self._lock:
            if channel not in self._connections:
                self._connections[channel] = set()
            self._connections[channel].add(websocket)

    async def unregister(self, channel: str, websocket) -> None:
        async with self._lock:
            if channel in self._connections:
                self._connections[channel].discard(websocket)
                if not self._connections[channel]:
                    del self._connections[channel]

    async def broadcast(self, channel: str, message: Dict) -> int:
        sent = 0
        async with self._lock:
            connections = self._connections.get(channel, set()).copy()
        for ws in connections:
            try:
                await ws.send_json(message)
                sent += 1
            except Exception:
                async with self._lock:
                    self._connections.get(channel, set()).discard(ws)
        return sent

    async def broadcast_all(self, message: Dict) -> int:
        total = 0
        async with self._lock:
            channels = list(self._connections.keys())
        for channel in channels:
            total += await self.broadcast(channel, message)
        return total


ws_manager = WebSocketManager()


class ArgusAPI:
    """Main API class integrating all backend components."""

    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}
        self.db = None
        self.vision = None
        self.pipeline = None
        self.events = None
        self.analytics = None
        self.rules = None
        self.security = None
        self.cache = None
        self.workers = None
        self.notifications = None
        self.metrics = None
        self._initialized = False

    async def initialize(self) -> None:
        from ..database import get_database, DatabaseManager
        from ..vision import VisionEngine
        from ..pipeline import VideoPipeline
        from ..events import EventManager
        from ..analytics import AnalyticsEngine
        from ..rules import RuleEngine
        from ..security import SecurityManager
        from ..cache import CacheManager
        from ..workers import WorkerManager
        from ..notifications import NotificationManager
        from ..metrics import MetricsCollector

        self.db = get_database()
        self.vision = VisionEngine(self.config.get("vision", {}))
        self.vision.initialize()
        self.pipeline = VideoPipeline(self.config.get("pipeline", {}))
        self.events = EventManager(self.db, self.config.get("events", {}))
        self.analytics = AnalyticsEngine(self.db, self.config.get("analytics", {}))
        self.rules = RuleEngine()
        self.rules.load_from_db(self.db)
        self.security = SecurityManager(self.config.get("security", {}))
        self.security.set_db(self.db)
        self.cache = CacheManager(self.config.get("cache", "memory"))
        self.workers = WorkerManager()
        self.workers.start()
        self.notifications = NotificationManager()
        self.metrics = MetricsCollector(self.config.get("metrics", {}))

        self.events.on_event(self.notifications.notify_event)
        self.metrics.start_collecting()

        self._initialized = True
        logger.info("ArgusAPI initialized successfully")

    async def shutdown(self) -> None:
        if self.workers:
            self.workers.stop()
        if self.metrics:
            self.metrics.close()
        if self.pipeline:
            self.pipeline.stop()
        if self.vision:
            self.vision.close()
        self._initialized = False
        logger.info("ArgusAPI shut down")

    def require_auth(self, token: str) -> Optional[Dict]:
        if not self.security:
            return None
        payload = self.security.jwt.verify_token(token)
        if not payload:
            return None
        return payload

    def check_permission(self, user: Dict, permission: str) -> bool:
        from ..security import ROLES
        role = user.get("role", "viewer")
        role_perms = set(ROLES.get(role, ROLES["viewer"])["permissions"])
        return "admin" in role_perms or permission in role_perms
