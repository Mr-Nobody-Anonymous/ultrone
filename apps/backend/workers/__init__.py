"""
Worker Manager — Background task processing, thread pools, async workers, scheduled tasks.
"""

import os
import time
import json
import logging
import threading
import enum
import concurrent.futures
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Set
from queue import PriorityQueue

logger = logging.getLogger("argus.workers")


class TaskPriority(enum.Enum):
    LOW = 0
    NORMAL = 1
    HIGH = 2
    CRITICAL = 3


@dataclass(order=True)
class Task:
    id: str = field(compare=False)
    name: str = field(compare=False)
    fn: Callable = field(compare=False)
    args: tuple = field(default_factory=tuple, compare=False)
    kwargs: Dict = field(default_factory=dict, compare=False)
    priority: int = 1
    created_at: float = field(default_factory=time.time, compare=False)
    timeout: Optional[float] = field(default=None, compare=False)
    retry_count: int = field(default=0, compare=False)
    max_retries: int = field(default=3, compare=False)
    result: Any = field(default=None, compare=False)
    error: Optional[str] = field(default=None, compare=False)
    status: str = field(default="pending", compare=False)

    def __post_init__(self):
        if isinstance(self.fn, str):
            raise ValueError("Task requires a callable function")


class WorkerPool:
    """Thread pool for executing background tasks."""

    def __init__(self, max_workers: int = 4, name: str = "argus"):
        self.max_workers = max_workers
        self.name = name
        self._executor = concurrent.futures.ThreadPoolExecutor(
            max_workers=max_workers, thread_name_prefix=name,
        )
        self._tasks: Dict[str, concurrent.futures.Future] = {}
        self._running = False

    def submit(self, task: Task) -> str:
        future = self._executor.submit(self._run_task, task)
        self._tasks[task.id] = future
        logger.debug(f"Task submitted: {task.name} ({task.id})")
        return task.id

    def _run_task(self, task: Task) -> Any:
        task.status = "running"
        try:
            if task.timeout:
                with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                    future = pool.submit(task.fn, *task.args, **task.kwargs)
                    task.result = future.result(timeout=task.timeout)
            else:
                task.result = task.fn(*task.args, **task.kwargs)
            task.status = "completed"
            logger.info(f"Task completed: {task.name} ({task.id})")
            return task.result
        except Exception as e:
            task.status = "failed"
            task.error = str(e)
            if task.retry_count < task.max_retries:
                task.retry_count += 1
                logger.warning(f"Task retrying: {task.name} ({task.id}), attempt {task.retry_count}")
                return self._run_task(task)
            logger.error(f"Task failed: {task.name} ({task.id}): {e}")
            raise

    def get_result(self, task_id: str, timeout: Optional[float] = None) -> Any:
        future = self._tasks.get(task_id)
        if future:
            return future.result(timeout=timeout)
        return None

    def cancel(self, task_id: str) -> bool:
        future = self._tasks.get(task_id)
        if future:
            return future.cancel()
        return False

    def shutdown(self, wait: bool = True) -> None:
        self._executor.shutdown(wait=wait)
        logger.info(f"WorkerPool shutdown: {self.name}")


class WorkerManager:
    """Manages multiple worker pools for different task types."""

    def __init__(self):
        self._pools: Dict[str, WorkerPool] = {}
        self._task_queue: PriorityQueue = PriorityQueue()
        self._scheduled_tasks: List[Dict] = []
        self._running = False
        self._dispatcher_thread: Optional[threading.Thread] = None
        self._default_pool = WorkerPool(max_workers=4, name="default")

    def create_pool(self, name: str, max_workers: int = 2) -> WorkerPool:
        pool = WorkerPool(max_workers=max_workers, name=name)
        self._pools[name] = pool
        return pool

    def submit(self, task: Task, pool_name: Optional[str] = None) -> str:
        pool = self._pools.get(pool_name) if pool_name else self._default_pool
        if not pool:
            pool = self._default_pool
        return pool.submit(task)

    def schedule(self, name: str, fn: Callable, interval: float, repeat: bool = True) -> str:
        task = Task(
            id=f"scheduled_{name}_{int(time.time())}",
            name=name,
            fn=fn,
            priority=TaskPriority.HIGH.value,
        )
        self._scheduled_tasks.append({
            "task": task,
            "interval": interval,
            "repeat": repeat,
            "last_run": 0,
        })
        return task.id

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._dispatcher_thread = threading.Thread(
            target=self._dispatch_loop, daemon=True, name="worker-dispatcher"
        )
        self._dispatcher_thread.start()
        logger.info("WorkerManager started")

    def stop(self) -> None:
        self._running = False
        if self._dispatcher_thread:
            self._dispatcher_thread.join(timeout=5)
        for pool in self._pools.values():
            pool.shutdown()
        self._default_pool.shutdown()
        logger.info("WorkerManager stopped")

    def _dispatch_loop(self) -> None:
        while self._running:
            try:
                now = time.time()
                for scheduled in self._scheduled_tasks[:]:
                    if now - scheduled["last_run"] >= scheduled["interval"]:
                        scheduled["last_run"] = now
                        new_task = Task(
                            id=f"{scheduled['task'].id}_{int(now)}",
                            name=scheduled['task'].name,
                            fn=scheduled['task'].fn,
                            priority=scheduled['task'].priority,
                        )
                        self.submit(new_task)
                        if not scheduled["repeat"]:
                            self._scheduled_tasks.remove(scheduled)
                while not self._task_queue.empty():
                    task = self._task_queue.get_nowait()
                    self.submit(task)
                time.sleep(0.1)
            except Exception as e:
                logger.error(f"Dispatch error: {e}")

    def get_stats(self) -> Dict:
        return {
            "default_pool": {"max_workers": self._default_pool.max_workers},
            "custom_pools": list(self._pools.keys()),
            "scheduled_tasks": len(self._scheduled_tasks),
            "running": self._running,
        }
