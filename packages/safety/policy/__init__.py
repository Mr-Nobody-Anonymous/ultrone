"""
ULTRONE Safety Policy Enforcement.

Defines and enforces safety policies across the platform:
- Human-in-the-loop requirements
- Escalation thresholds
- Autonomy boundaries
- Operational constraints
- Ethical guidelines
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class PolicyAction(str, Enum):
    """Actions a safety policy can mandate."""
    ALLOW = "allow"
    DENY = "deny"
    REQUIRE_APPROVAL = "require_approval"
    ESCALATE = "escalate"
    LOG_ONLY = "log_only"
    RATE_LIMIT = "rate_limit"


@dataclass
class SafetyPolicy:
    """A safety policy rule."""
    policy_id: str = ""
    name: str = ""
    description: str = ""
    action: PolicyAction = PolicyAction.LOG_ONLY
    conditions: Dict[str, Any] = field(default_factory=dict)
    priority: int = 0
    enabled: bool = True


class PolicyEngine:
    """Evaluates safety policies against proposed actions."""

    def __init__(self) -> None:
        self._policies: List[SafetyPolicy] = []

    def add_policy(self, policy: SafetyPolicy) -> None:
        self._policies.append(policy)
        self._policies.sort(key=lambda p: p.priority, reverse=True)

    def evaluate(self, context: Dict[str, Any]) -> PolicyAction:
        """Evaluate all policies and return the highest-priority action."""
        for policy in self._policies:
            if policy.enabled:
                return policy.action
        return PolicyAction.ALLOW


__all__ = ["PolicyAction", "SafetyPolicy", "PolicyEngine"]
