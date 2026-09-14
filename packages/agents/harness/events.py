# Copyright (c) Ultrone Contributors. All rights reserved.
"""Typed event definitions for Agent Harness execution."""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Optional


class HarnessEventType(str, Enum):
    """Event types emitted during harness execution lifecycle."""

    HARNESS_STARTED = "HARNESS_STARTED"
    GOAL_SET = "GOAL_SET"
    PLAN_CREATED = "PLAN_CREATED"
    STEP_STARTED = "STEP_STARTED"
    STEP_COMPLETED = "STEP_COMPLETED"
    STEP_FAILED = "STEP_FAILED"
    OBSERVATION_COLLECTED = "OBSERVATION_COLLECTED"
    EVALUATION_STARTED = "EVALUATION_STARTED"
    EVALUATION_PASSED = "EVALUATION_PASSED"
    EVALUATION_FAILED = "EVALUATION_FAILED"
    CHECKPOINT_SAVED = "CHECKPOINT_SAVED"
    CHECKPOINT_RESTORED = "CHECKPOINT_RESTORED"
    RECOVERY_TRIGGERED = "RECOVERY_TRIGGERED"
    HARNESS_COMPLETED = "HARNESS_COMPLETED"
    HARNESS_FAILED = "HARNESS_FAILED"
    HARNESS_CANCELLED = "HARNESS_CANCELLED"


@dataclass
class HarnessEvent:
    """Individual event object recorded by the harness event stream."""

    event_type: HarnessEventType
    task_id: str
    payload: Dict[str, Any] = field(default_factory=dict)
    event_id: str = field(default_factory=lambda: f"evt-{uuid.uuid4().hex[:8]}")
    timestamp: float = field(default_factory=time.time)
    parent_event_id: Optional[str] = None
