"""
ULTRONE Safety Constraints.

Defines hard and soft constraints on system behavior:
- Operational boundaries (geofences, time windows)
- Resource limits (compute, memory, API calls)
- Authority levels (what each role can do)
- Classification controls
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class ConstraintType(str, Enum):
    """Types of safety constraints."""
    GEOFENCE = "geofence"
    TIME_WINDOW = "time_window"
    RESOURCE_LIMIT = "resource_limit"
    AUTHORITY_LEVEL = "authority_level"
    CLASSIFICATION = "classification"
    RATE_LIMIT = "rate_limit"
    CUSTOM = "custom"


@dataclass
class Constraint:
    """A safety constraint definition."""
    constraint_id: str = ""
    name: str = ""
    type: ConstraintType = ConstraintType.CUSTOM
    parameters: Dict[str, Any] = field(default_factory=dict)
    hard: bool = True  # Hard constraints cannot be overridden
    enabled: bool = True


@dataclass
class ConstraintViolation:
    """Record of a constraint violation."""
    constraint_id: str = ""
    violation_type: str = ""
    details: str = ""
    severity: str = "warning"
    timestamp: str = ""


__all__ = ["ConstraintType", "Constraint", "ConstraintViolation"]
