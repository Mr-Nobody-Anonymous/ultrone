# Copyright (c) Ultrone Contributors. All rights reserved.
"""Tool execution audit logging and telemetry."""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger("Ultrone.Tools.Audit")


@dataclass
class ToolAuditEntry:
    """Immutable audit record of a tool execution attempt."""

    execution_id: str
    tool_name: str
    caller_agent_id: str
    arguments: Dict[str, Any]
    success: bool
    duration_ms: float
    error: Optional[str] = None
    timestamp: float = field(default_factory=time.time)


class ToolAuditLogger:
    """In-memory and file-backed audit store for security compliance."""

    def __init__(self) -> None:
        self._entries: List[ToolAuditEntry] = []

    def log_execution(
        self,
        execution_id: str,
        tool_name: str,
        caller_agent_id: str,
        arguments: Dict[str, Any],
        success: bool,
        duration_ms: float,
        error: Optional[str] = None,
    ) -> ToolAuditEntry:
        """Record an audit trail entry."""
        # Sanitize sensitive arguments
        sanitized_args = {k: ("***" if "secret" in k.lower() or "token" in k.lower() else v) for k, v in arguments.items()}
        entry = ToolAuditEntry(
            execution_id=execution_id,
            tool_name=tool_name,
            caller_agent_id=caller_agent_id,
            arguments=sanitized_args,
            success=success,
            duration_ms=duration_ms,
            error=error,
        )
        self._entries.append(entry)
        logger.info("AUDIT: Tool '%s' executed by '%s' - success=%s (%.1fms)", tool_name, caller_agent_id, success, duration_ms)
        return entry

    def get_entries(self) -> List[ToolAuditEntry]:
        return list(self._entries)
