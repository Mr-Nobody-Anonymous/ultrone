# Copyright (c) Ultrone Contributors. All rights reserved.
"""Dynamic role assignment for multi-agent teams."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from .base import BaseCoordinator, CoordinationConfig

logger = logging.getLogger("Ultrone.Brain.Reasoning.Coordination.RoleAssignment")


@dataclass
class RoleConfig(CoordinationConfig):
    """Configuration for role assignment."""
    role_set: List[str] = None  # type: ignore
    assignment_strategy: str = "capability"


class RoleAssignment(BaseCoordinator):
    """Dynamic role assignment based on agent capabilities."""

    def __init__(self, config: Optional[RoleConfig] = None):
        super().__init__(config or RoleConfig(role_set=["scout", "attacker", "defender", "support"]))
        self._config: RoleConfig = self.config  # type: ignore

    def coordinate(self, context: Dict[str, Any]) -> Dict[str, Any]:
        from collections import Counter
        roles = {}
        for i, aid in enumerate(self._agents):
            roles[aid] = self._config.role_set[i % len(self._config.role_set)]
        return {"roles": roles, "distribution": dict(Counter(roles.values()))}

    def get_stats(self) -> Dict[str, Any]:
        return {"type": "RoleAssignment"}