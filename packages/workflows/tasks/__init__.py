"""ULTRONE Workflows - Task queue, async dispatcher, and background execution status."""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class TaskStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class WorkflowTask:
    """An asynchronous task managed by the workflow execution engine."""
    task_id: str
    task_name: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    status: TaskStatus = TaskStatus.QUEUED
    progress_percent: float = 0.0
    result: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)

    def update_progress(self, percent: float) -> None:
        self.progress_percent = min(100.0, max(0.0, percent))
        self.status = TaskStatus.RUNNING
        self.updated_at = time.time()

    def complete(self, result: Dict[str, Any]) -> None:
        self.status = TaskStatus.COMPLETED
        self.progress_percent = 100.0
        self.result = result
        self.updated_at = time.time()

    def fail(self, error: str) -> None:
        self.status = TaskStatus.FAILED
        self.error_message = error
        self.updated_at = time.time()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_id": self.task_id,
            "task_name": self.task_name,
            "status": self.status.value,
            "progress_percent": self.progress_percent,
            "result": self.result,
            "error_message": self.error_message,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


class TaskQueue:
    """In-memory task dispatcher and state store."""

    def __init__(self):
        self._tasks: Dict[str, WorkflowTask] = {}

    def dispatch(self, task_name: str, parameters: Dict[str, Any]) -> WorkflowTask:
        task_id = f"task_{uuid.uuid4().hex[:8]}"
        task = WorkflowTask(task_id=task_id, task_name=task_name, parameters=parameters)
        self._tasks[task_id] = task
        return task

    def get_task(self, task_id: str) -> Optional[WorkflowTask]:
        return self._tasks.get(task_id)

    def list_tasks(self) -> List[WorkflowTask]:
        return list(self._tasks.values())


__all__ = ["TaskStatus", "WorkflowTask", "TaskQueue"]
