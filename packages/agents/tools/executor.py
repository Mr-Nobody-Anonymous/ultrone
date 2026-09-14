# Copyright (c) Ultrone Contributors. All rights reserved.
"""ToolRuntime: Coordinates validation, permission checks, execution, and audit."""

from __future__ import annotations

import logging
import time
from typing import Any, Dict, Optional

from .audit import ToolAuditLogger
from .permissions import PermissionDeniedError, ToolPermissionChecker
from .registry import ToolRegistry
from .schema import ToolResult

logger = logging.getLogger("Ultrone.Tools.Runtime")


class ToolRuntime:
    """Production-grade runtime executing tools through strict safety layers."""

    def __init__(
        self,
        registry: Optional[ToolRegistry] = None,
        permission_checker: Optional[ToolPermissionChecker] = None,
        audit_logger: Optional[ToolAuditLogger] = None,
    ) -> None:
        self.registry = registry or ToolRegistry()
        self.permission_checker = permission_checker or ToolPermissionChecker()
        self.audit_logger = audit_logger or ToolAuditLogger()

    def execute(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        caller_agent_id: str = "system",
    ) -> ToolResult:
        """Execute a tool through the full validation, security, and audit pipeline.

        Pipeline:
        1. Tool Lookup
        2. Permission Check (RBAC + Human Approval)
        3. Schema Validation
        4. Invocation & Error Handling
        5. Audit Trail Recording
        6. Return Normalized ToolResult
        """
        start_time = time.time()
        tool_def = self.registry.get_definition(tool_name)
        if not tool_def:
            duration = (time.time() - start_time) * 1000.0
            err_msg = f"Tool '{tool_name}' not found in registry."
            self.audit_logger.log_execution(
                execution_id="not-found",
                tool_name=tool_name,
                caller_agent_id=caller_agent_id,
                arguments=arguments,
                success=False,
                duration_ms=duration,
                error=err_msg,
            )
            return ToolResult(tool_name=tool_name, success=False, error=err_msg, duration_ms=duration)

        # 2. Permission Check
        try:
            self.permission_checker.check_permission(tool_def, arguments)
        except PermissionDeniedError as perm_err:
            duration = (time.time() - start_time) * 1000.0
            err_msg = str(perm_err)
            self.audit_logger.log_execution(
                execution_id="perm-denied",
                tool_name=tool_name,
                caller_agent_id=caller_agent_id,
                arguments=arguments,
                success=False,
                duration_ms=duration,
                error=err_msg,
            )
            return ToolResult(tool_name=tool_name, success=False, error=err_msg, duration_ms=duration)

        # 3. Schema Validation
        try:
            tool_def.validate_arguments(arguments)
        except ValueError as val_err:
            duration = (time.time() - start_time) * 1000.0
            err_msg = f"Argument validation error: {val_err}"
            self.audit_logger.log_execution(
                execution_id="schema-err",
                tool_name=tool_name,
                caller_agent_id=caller_agent_id,
                arguments=arguments,
                success=False,
                duration_ms=duration,
                error=err_msg,
            )
            return ToolResult(tool_name=tool_name, success=False, error=err_msg, duration_ms=duration)

        # 4. Invocation
        handler = self.registry.get_handler(tool_name)
        if not handler:
            duration = (time.time() - start_time) * 1000.0
            err_msg = f"Tool '{tool_name}' definition exists but handler is missing."
            return ToolResult(tool_name=tool_name, success=False, error=err_msg, duration_ms=duration)

        try:
            raw_output = handler(**arguments)
            duration = (time.time() - start_time) * 1000.0
            result = ToolResult(
                tool_name=tool_name,
                success=True,
                output=raw_output,
                duration_ms=duration,
            )
            self.audit_logger.log_execution(
                execution_id=result.execution_id,
                tool_name=tool_name,
                caller_agent_id=caller_agent_id,
                arguments=arguments,
                success=True,
                duration_ms=duration,
            )
            return result
        except Exception as exc:
            duration = (time.time() - start_time) * 1000.0
            err_msg = f"Tool execution failed: {exc}"
            logger.error("Error executing %s: %s", tool_name, exc)
            self.audit_logger.log_execution(
                execution_id="exec-err",
                tool_name=tool_name,
                caller_agent_id=caller_agent_id,
                arguments=arguments,
                success=False,
                duration_ms=duration,
                error=err_msg,
            )
            return ToolResult(
                tool_name=tool_name,
                success=False,
                error=err_msg,
                duration_ms=duration,
            )
