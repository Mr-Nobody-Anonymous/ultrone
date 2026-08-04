"""
Argus — Task Scheduler
======================
Schedules and executes periodic tasks with retry, monitoring, and concurrency.
"""

from __future__ import annotations

import threading
import time
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

from .base import (
    ScheduledTask,
    SchedulerConfig,
    TaskResult,
    TaskStatus,
)


class TaskScheduler:
    """Schedules and executes periodic tasks."""

    def __init__(self, config: Optional[SchedulerConfig] = None) -> None:
        self._config = config or SchedulerConfig()
        self._tasks: Dict[str, ScheduledTask] = {}
        self._results: List[TaskResult] = []
        self._running: bool = False
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()

    def schedule(
        self,
        name: str,
        callable: Callable[..., Any],
        *,
        interval_seconds: Optional[float] = None,
        args: Optional[List[Any]] = None,
        kwargs: Optional[Dict[str, Any]] = None,
        max_retries: int = 3,
    ) -> ScheduledTask:
        """Schedule a new periodic task."""
        task = ScheduledTask(
            name=name,
            callable=callable,
            interval_seconds=interval_seconds or self._config.default_interval_seconds,
            max_retries=max_retries,
            args=args or [],
            kwargs=kwargs or {},
        )
        with self._lock:
            self._tasks[task.task_id] = task
        return task

    def unschedule(self, task_id: str) -> bool:
        """Remove a scheduled task."""
        with self._lock:
            return self._tasks.pop(task_id, None) is not None

    def get_task(self, task_id: str) -> Optional[ScheduledTask]:
        return self._tasks.get(task_id)

    def all_tasks(self) -> List[ScheduledTask]:
        return list(self._tasks.values())

    def run_task(self, task: ScheduledTask) -> TaskResult:
        """Execute a single task with retries."""
        result = TaskResult(task_id=task.task_id, status=TaskStatus.RUNNING)
        task.status = TaskStatus.RUNNING

        for attempt in range(task.max_retries + 1):
            try:
                if task.callable is None:
                    raise ValueError(f"Task {task.name} has no callable")
                output = task.callable(*task.args, **task.kwargs)
                task.run_count += 1
                task.status = TaskStatus.COMPLETED
                task.schedule_next()
                return result.complete(TaskStatus.COMPLETED, result=output)
            except Exception as e:
                if attempt < task.max_retries:
                    time.sleep(self._config.retry_delay_seconds)
                    result.retry_count += 1
                else:
                    task.status = TaskStatus.FAILED
                    return result.complete(TaskStatus.FAILED, error=str(e))

        return result.complete(TaskStatus.FAILED, error="Max retries exceeded")

    def run_due(self) -> List[TaskResult]:
        """Run all tasks that are due."""
        results: List[TaskResult] = []
        now = datetime.utcnow()

        with self._lock:
            due_tasks = [
                task for task in self._tasks.values()
                if task.should_run(now)
            ]

        for task in due_tasks:
            result = self.run_task(task)
            results.append(result)
            self._results.append(result)

        return results

    def start(self) -> None:
        """Start the scheduler loop in a background thread."""
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        """Stop the scheduler loop."""
        self._running = False
        if self._thread is not None:
            self._thread.join(timeout=5.0)
            self._thread = None

    def _loop(self) -> None:
        """Main scheduler loop."""
        while self._running:
            try:
                self.run_due()
            except Exception:
                pass
            time.sleep(1.0)

    def results(self, limit: Optional[int] = None) -> List[TaskResult]:
        results = self._results
        if limit is not None:
            results = results[-limit:]
        return list(results)

    @property
    def task_count(self) -> int:
        return len(self._tasks)

    @property
    def is_running(self) -> bool:
        return self._running