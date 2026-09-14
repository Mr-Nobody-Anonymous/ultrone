# Copyright (c) Ultrone Contributors. All rights reserved.
"""Harness data schemas and type definitions."""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class LifecycleState(str, Enum):
    """Universal Agent Lifecycle states."""

    CREATED = "CREATED"
    PLANNING = "PLANNING"
    READY = "READY"
    EXECUTING = "EXECUTING"
    OBSERVING = "OBSERVING"
    VERIFYING = "VERIFYING"
    RECOVERING = "RECOVERING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"

    @property
    def is_terminal(self) -> bool:
        return self in (
            LifecycleState.COMPLETED,
            LifecycleState.FAILED,
            LifecycleState.CANCELLED,
        )


class EvaluationStatus(str, Enum):
    """Independent Evaluator verdicts (default is FAIL)."""

    PASS = "PASS"
    FAIL = "FAIL"
    NEEDS_REVISION = "NEEDS_REVISION"


@dataclass
class Goal:
    """The formal goal provided to the agent harness."""

    description: str
    goal_id: str = field(default_factory=lambda: f"goal-{uuid.uuid4().hex[:8]}")
    acceptance_criteria: List[str] = field(default_factory=list)
    constraints: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)

    def validate(self) -> None:
        if not self.description or not self.description.strip():
            raise ValueError("Goal description must be non-empty.")


@dataclass
class ExecutionStep:
    """A discrete execution step recorded in the task history."""

    step_id: str = field(default_factory=lambda: f"step-{uuid.uuid4().hex[:8]}")
    step_number: int = 1
    action: str = ""
    status: str = "PENDING"  # PENDING, RUNNING, SUCCESS, FAILED, RETRIED
    input_data: Dict[str, Any] = field(default_factory=dict)
    output_data: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    duration_ms: float = 0.0
    timestamp: float = field(default_factory=time.time)


@dataclass
class EvaluationResult:
    """Outcome of an independent fresh-context evaluation."""

    status: EvaluationStatus = EvaluationStatus.FAIL  # default-fail criteria
    score: float = 0.0
    reason: str = "Default-fail: evaluation pending"
    passed_criteria: List[str] = field(default_factory=list)
    failed_criteria: List[str] = field(default_factory=list)
    evidence: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)

    @property
    def passed(self) -> bool:
        return self.status == EvaluationStatus.PASS


@dataclass
class CheckpointData:
    """Serializable task execution state for persistent resume."""

    task_id: str
    goal: Dict[str, Any]
    current_phase: str
    completed_steps: List[Dict[str, Any]] = field(default_factory=list)
    failed_steps: List[Dict[str, Any]] = field(default_factory=list)
    working_state: Dict[str, Any] = field(default_factory=dict)
    memory_refs: List[str] = field(default_factory=list)
    tool_state: Dict[str, Any] = field(default_factory=dict)
    model: str = "default"
    context_summary: str = ""
    last_commit: str = ""
    timestamp: float = field(default_factory=time.time)
    version: str = "1.0.0"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_id": self.task_id,
            "goal": self.goal,
            "current_phase": self.current_phase,
            "completed_steps": self.completed_steps,
            "failed_steps": self.failed_steps,
            "working_state": self.working_state,
            "memory_refs": self.memory_refs,
            "tool_state": self.tool_state,
            "model": self.model,
            "context_summary": self.context_summary,
            "last_commit": self.last_commit,
            "timestamp": self.timestamp,
            "version": self.version,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> CheckpointData:
        return cls(
            task_id=data["task_id"],
            goal=data.get("goal", {}),
            current_phase=data.get("current_phase", "CREATED"),
            completed_steps=data.get("completed_steps", []),
            failed_steps=data.get("failed_steps", []),
            working_state=data.get("working_state", {}),
            memory_refs=data.get("memory_refs", []),
            tool_state=data.get("tool_state", {}),
            model=data.get("model", "default"),
            context_summary=data.get("context_summary", ""),
            last_commit=data.get("last_commit", ""),
            timestamp=data.get("timestamp", time.time()),
            version=data.get("version", "1.0.0"),
        )


@dataclass
class HarnessConfig:
    """Execution parameters and guardrails for AgentHarness."""

    max_steps: int = 50
    max_retries_per_step: int = 3
    timeout_seconds: float = 300.0
    require_independent_evaluation: bool = True
    auto_checkpoint: bool = True
    checkpoint_dir: Optional[str] = None
    model_name: str = "default"
