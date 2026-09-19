"""ULTRONE Device Interface Standard (UDIS) - Safety Limits & Constraints.

Implements MHS-aligned physical and simulation safety limit specifications,
parameter boundaries, and dynamic limit verification.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class SafetyConstraint:
    """Explicit safety invariant enforced before device execution."""
    constraint_id: str
    parameter: str
    operator: str  # '<=', '>=', '==', '<', '>', 'in', 'range'
    limit_value: Any
    description: str = ""
    is_hard_limit: bool = True

    def validate(self, val: Any) -> Tuple[bool, Optional[str]]:
        try:
            if self.operator == "<=":
                ok = val <= self.limit_value
            elif self.operator == ">=":
                ok = val >= self.limit_value
            elif self.operator == "<":
                ok = val < self.limit_value
            elif self.operator == ">":
                ok = val > self.limit_value
            elif self.operator == "==":
                ok = val == self.limit_value
            elif self.operator == "in":
                ok = val in self.limit_value
            elif self.operator == "range":
                low, high = self.limit_value
                ok = low <= val <= high
            else:
                return False, f"Unknown operator {self.operator}"

            if not ok:
                return False, (
                    f"Constraint violation [{self.constraint_id}]: {self.parameter}={val} "
                    f"violates rule '{self.operator} {self.limit_value}' ({self.description})"
                )
            return True, None
        except Exception as e:
            return False, f"Constraint check error [{self.constraint_id}]: {e}"


@dataclass
class DeviceSafetyLimits:
    """Comprehensive device safety profile."""
    device_id: str
    simulation_only: bool = True
    e_stop_available: bool = True
    constraints: List[SafetyConstraint] = field(default_factory=list)

    def verify_parameters(self, params: Dict[str, Any]) -> Tuple[bool, List[str]]:
        violations = []
        for constraint in self.constraints:
            if constraint.parameter in params:
                val = params[constraint.parameter]
                passed, reason = constraint.validate(val)
                if not passed and reason:
                    violations.append(reason)
        return len(violations) == 0, violations
