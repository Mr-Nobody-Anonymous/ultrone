# Copyright (c) Ultrone Contributors. All rights reserved.
"""Execution policies and operator-control hooks."""

from __future__ import annotations

import logging
from typing import Any, Callable, Dict, Optional

logger = logging.getLogger("Ultrone.Harness.Policies")


class ExecutionPolicy:
    """Configurable execution guards and operator approval hooks."""

    def __init__(
        self,
        require_approval_for_tools: Optional[list[str]] = None,
        operator_hook: Optional[Callable[[str, Dict[str, Any]], bool]] = None,
        max_total_steps: int = 100,
    ) -> None:
        self.require_approval_for_tools = set(require_approval_for_tools or [])
        self.operator_hook = operator_hook
        self.max_total_steps = max_total_steps

    def check_tool_permission(self, tool_name: str, arguments: Dict[str, Any]) -> bool:
        """Evaluate if tool invocation is permitted or requires operator consent."""
        if tool_name in self.require_approval_for_tools:
            if self.operator_hook:
                return self.operator_hook(tool_name, arguments)
            logger.warning("Tool %s requires operator approval, but no operator hook registered.", tool_name)
            return False
        return True
