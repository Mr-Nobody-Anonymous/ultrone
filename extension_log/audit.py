# Copyright (c) Ultrone Contributors. All rights reserved.
"""Audit logger — comprehensive logging for the research platform."""

from __future__ import annotations

import json
import logging
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger("Ultrone.ExtensionLog")


class LogLevel(Enum):
    """Log severity levels."""
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class LogCategory(Enum):
    """Categories of log entries."""
    DECISION = "decision"
    EXPERIMENT = "experiment"
    BENCHMARK = "benchmark"
    CODE_GENERATION = "code_generation"
    FILE_MODIFICATION = "file_modification"
    TEST_RESULT = "test_result"
    DEPLOYMENT = "deployment"
    CITATION = "citation"
    REASONING = "reasoning"
    RECOMMENDATION = "recommendation"
    MODULE = "module"
    ARCHITECTURE = "architecture"
    OPTIMIZATION = "optimization"
    FAILURE = "failure"
    WARNING = "warning"
    EXCEPTION = "exception"
    GENERAL = "general"


@dataclass
class LogEntry:
    """A single log entry."""
    log_id: str = field(default_factory=lambda: f"LOG-{uuid.uuid4().hex[:8]}")
    timestamp: float = field(default_factory=time.time)
    level: LogLevel = LogLevel.INFO
    category: LogCategory = LogCategory.GENERAL
    component: str = ""
    message: str = ""
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "log_id": self.log_id,
            "timestamp": self.timestamp,
            "level": self.level.value,
            "category": self.category.value,
            "component": self.component,
            "message": self.message,
            "details": self.details,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "LogEntry":
        return cls(
            log_id=data.get("log_id", f"LOG-{uuid.uuid4().hex[:8]}"),
            timestamp=data.get("timestamp", time.time()),
            level=LogLevel(data.get("level", "info")),
            category=LogCategory(data.get("category", "general")),
            component=data.get("component", ""),
            message=data.get("message", ""),
            details=data.get("details", {}),
        )


class AuditLogger:
    """Comprehensive audit logger with multiple storage backends."""

    def __init__(self, stores: Optional[List[Any]] = None):
        self.stores = stores or []
        self._entries: List[LogEntry] = []

    def add_store(self, store: Any) -> None:
        """Add a log store."""
        self.stores.append(store)

    def log(
        self,
        message: str,
        level: LogLevel = LogLevel.INFO,
        category: LogCategory = LogCategory.GENERAL,
        component: str = "",
        details: Optional[Dict[str, Any]] = None,
    ) -> LogEntry:
        """Log an entry to all stores."""
        entry = LogEntry(
            level=level,
            category=category,
            component=component,
            message=message,
            details=details or {},
        )
        self._entries.append(entry)

        # Write to all stores
        for store in self.stores:
            try:
                store.write(entry)
            except Exception as e:
                logger.error("Failed to write to log store %s: %s", type(store).__name__, e)

        return entry

    # Convenience methods
    def info(self, message: str, category: LogCategory = LogCategory.GENERAL, component: str = "", details: Dict[str, Any] = None) -> LogEntry:
        return self.log(message, LogLevel.INFO, category, component, details)

    def warning(self, message: str, category: LogCategory = LogCategory.WARNING, component: str = "", details: Dict[str, Any] = None) -> LogEntry:
        return self.log(message, LogLevel.WARNING, category, component, details)

    def error(self, message: str, category: LogCategory = LogCategory.FAILURE, component: str = "", details: Dict[str, Any] = None) -> LogEntry:
        return self.log(message, LogLevel.ERROR, category, component, details)

    def critical(self, message: str, category: LogCategory = LogCategory.EXCEPTION, component: str = "", details: Dict[str, Any] = None) -> LogEntry:
        return self.log(message, LogLevel.CRITICAL, category, component, details)

    def get_entries(self, limit: int = 100) -> List[LogEntry]:
        """Get recent log entries."""
        return self._entries[-limit:]

    def get_stats(self) -> Dict[str, Any]:
        return {
            "type": "AuditLogger",
            "entries_logged": len(self._entries),
            "stores": [type(s).__name__ for s in self.stores],
        }