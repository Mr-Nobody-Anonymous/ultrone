# Copyright (c) Ultrone Contributors. All rights reserved.
"""Tool permissions and security policy enforcement."""

from __future__ import annotations

import logging
from typing import Any, Callable, Dict, Optional, Set

from .schema import RiskLevel, ToolDefinition

logger = logging.getLogger("Ultrone.Tools.Permissions")


class PermissionDeniedError(Exception):
    """Raised when an agent lacks permission to execute a tool."""


class ToolPermissionChecker:
    """Enforces role-based permissions and human-in-the-loop approvals."""

    def __init__(
        self,
        allowed_tools: Optional[Set[str]] = None,
        max_allowed_risk: RiskLevel = RiskLevel.HIGH,
        human_approver: Optional[Callable[[ToolDefinition, Dict[str, Any]], bool]] = None,
    ) -> None:
        self.allowed_tools = allowed_tools  # None means all registered tools allowed
        self.max_allowed_risk = max_allowed_risk
        self.human_approver = human_approver

        self._risk_hierarchy = {
            RiskLevel.LOW: 1,
            RiskLevel.MEDIUM: 2,
            RiskLevel.HIGH: 3,
            RiskLevel.CRITICAL: 4,
        }

    def check_permission(self, tool: ToolDefinition, arguments: Dict[str, Any]) -> bool:
        """Verify if invocation is permitted under current security policy."""
        # 1. Whitelist check
        if self.allowed_tools is not None and tool.name not in self.allowed_tools:
            logger.warning("Tool %s not in allowed whitelist", tool.name)
            raise PermissionDeniedError(f"Tool '{tool.name}' is not permitted by whitelist policy.")

        # 2. Risk level check
        tool_risk_score = self._risk_hierarchy.get(tool.risk_level, 3)
        max_risk_score = self._risk_hierarchy.get(self.max_allowed_risk, 3)
        if tool_risk_score > max_risk_score:
            raise PermissionDeniedError(
                f"Tool '{tool.name}' risk level {tool.risk_level.value} exceeds allowed {self.max_allowed_risk.value}"
            )

        # 3. Human-in-the-loop approval check for CRITICAL or requires_approval
        if tool.requires_approval or tool.risk_level == RiskLevel.CRITICAL:
            if not self.human_approver:
                raise PermissionDeniedError(f"Tool '{tool.name}' requires operator approval, but no approver registered.")
            approved = self.human_approver(tool, arguments)
            if not approved:
                raise PermissionDeniedError(f"Tool '{tool.name}' execution rejected by human operator.")

        return True
