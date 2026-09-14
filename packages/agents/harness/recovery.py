# Copyright (c) Ultrone Contributors. All rights reserved.
"""Recovery and self-healing strategies for faulted agents."""

from __future__ import annotations

import logging
from enum import Enum
from typing import Any, Dict, Optional

from .checkpoint import CheckpointStore
from .schemas import CheckpointData, EvaluationResult

logger = logging.getLogger("Ultrone.Harness.Recovery")


class RecoveryAction(str, Enum):
    """Action chosen to recover from an execution failure."""

    RETRY_STEP = "RETRY_STEP"
    ROLLBACK_CHECKPOINT = "ROLLBACK_CHECKPOINT"
    COMPACT_CONTEXT = "COMPACT_CONTEXT"
    ESCALATE_HUMAN = "ESCALATE_HUMAN"
    TERMINATE = "TERMINATE"


class RecoveryManager:
    """Selects and applies recovery strategies based on failure telemetry."""

    def __init__(self, max_retries: int = 3, checkpoint_store: Optional[CheckpointStore] = None) -> None:
        self.max_retries = max_retries
        self.checkpoint_store = checkpoint_store
        self._retry_counts: Dict[str, int] = {}

    def decide_recovery(
        self,
        task_id: str,
        evaluation_or_error: Any,
        checkpoint: Optional[CheckpointData] = None,
    ) -> RecoveryAction:
        """Determine recovery action based on retry counts and failure nature."""
        count = self._retry_counts.get(task_id, 0)
        if count >= self.max_retries:
            logger.warning("Max recovery retries (%d) reached for task %s", self.max_retries, task_id)
            return RecoveryAction.ESCALATE_HUMAN

        self._retry_counts[task_id] = count + 1

        # If it's an evaluation result with specific failed criteria
        if isinstance(evaluation_or_error, EvaluationResult):
            if "context length" in evaluation_or_error.reason.lower() or "token" in evaluation_or_error.reason.lower():
                return RecoveryAction.COMPACT_CONTEXT
            if checkpoint and checkpoint.completed_steps:
                return RecoveryAction.ROLLBACK_CHECKPOINT
            return RecoveryAction.RETRY_STEP

        # If it's an exception or error string
        err_msg = str(evaluation_or_error).lower()
        if "token" in err_msg or "context" in err_msg or "maximum length" in err_msg:
            return RecoveryAction.COMPACT_CONTEXT
        if "permission" in err_msg or "forbidden" in err_msg:
            return RecoveryAction.ESCALATE_HUMAN

        return RecoveryAction.RETRY_STEP

    def reset(self, task_id: str) -> None:
        """Reset retry counts after successful recovery and completion."""
        self._retry_counts.pop(task_id, None)
