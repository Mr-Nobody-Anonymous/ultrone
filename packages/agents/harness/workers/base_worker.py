# Copyright (c) Ultrone Contributors. All rights reserved.
"""Base worker interface for execution underneath AgentHarness."""

from __future__ import annotations

import time
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from packages.agents.liveness.registry import LivenessRegistry


@dataclass
class WorkerInput:
    """Input payload delivered to a worker."""

    task_id: str
    goal_description: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    context_text: str = ""
    deadline: Optional[float] = None


@dataclass
class WorkerOutput:
    """Standardized output produced by a worker with verifiable evidence."""

    worker_id: str
    success: bool
    result: Any
    evidence: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    duration_ms: float = 0.0
    execution_id: str = field(default_factory=lambda: f"exec-{uuid.uuid4().hex[:8]}")


class HarnessWorker(ABC):
    """Abstract worker interface that plugs into AgentHarness."""

    def __init__(
        self,
        worker_id: str,
        capabilities: Optional[List[str]] = None,
        liveness_registry: Optional[LivenessRegistry] = None,
    ) -> None:
        self.worker_id = worker_id
        self.capabilities = list(capabilities or [])
        self.liveness_registry = liveness_registry

    def pulse_heartbeat(self, task_id: str, state: str = "EXECUTING", metadata: Optional[Dict] = None) -> None:
        """Send a liveness heartbeat pulse to the central registry."""
        if self.liveness_registry:
            self.liveness_registry.record_heartbeat(
                agent_id=self.worker_id,
                task_id=task_id,
                state=state,
                metadata=metadata or {},
            )

    @abstractmethod
    def execute(self, worker_input: WorkerInput) -> WorkerOutput:
        """Execute the delegated task and produce verifiable evidence."""
