"""
Argus — Scheduler Base Classes
=============================
Typed task, configuration, and result models for the scheduling system.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional


class TaskStatus(str, Enum):
    """Status of a scheduled task."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class SchedulerConfig:
    """Configuration for the task scheduler."""

    max_concurrent_tasks: int = 10
    default_interval_seconds: float = 60.0
    retry_count: int = 3
    retry_delay_seconds: float = 5.0
    enable_monitoring: bool = True


@dataclass
class ScheduledTask:
    """A scheduled task definition."""

    task_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    callable: Optional[Callable[..., Any]] = None
    interval_seconds: float = 60.0
    max_retries: int = 3
    enabled: bool = True
    last_run: Optional[datetime] = None
    next_run: Optional[datetime] = None
    run_count: int = 0
    status: TaskStatus = TaskStatus.PENDING
    args: List[Any] = field(default_factory=list)
    kwargs: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def should_run(self, now: Optional[datetime] = None) -> bool:
        """Check if the task should run now."""
        if not self.enabled:
            return False
        now = now or datetime.utcnow()
        if self.next_run is None:
            return True
        return now >= self.next_run

    def schedule_next(self, now: Optional[datetime] = None) -> None:
        """Schedule the next run."""
        now = now or datetime.utcnow()
        self.last_run = now
        self.next_run = datetime.fromtimestamp(
            now.timestamp() + self.interval_seconds
        )


@dataclass
class TaskResult:
    """Result of a task execution."""

    task_id: str
    status: TaskStatus
    started_at: datetime = field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    duration_seconds: float = 0.0
    result: Any = None
    error: Optional[str] = None
    retry_count: int = 0

    def complete(self, status: TaskStatus, result: Any = None, error: Optional[str] = None) -> "TaskResult":
        self.status = status
        self.result = result
        self.error = error
        self.completed_at = datetime.utcnow()
        self.duration_seconds = (self.completed_at - self.started_at).total_seconds()
        return self