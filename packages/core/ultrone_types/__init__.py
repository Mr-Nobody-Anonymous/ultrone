"""
ULTRONE Shared Type Definitions.

Central location for enums, type aliases, and protocol definitions
used across all ULTRONE packages.
"""
from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional, Protocol, runtime_checkable


# ─── Domain Enums ───────────────────────────────────────────────

class Domain(str, Enum):
    """Operational domains."""
    AIR = "air"
    LAND = "land"
    SEA = "sea"
    SPACE = "space"
    CYBER = "cyber"
    INFORMATION = "information"


class Priority(str, Enum):
    """Task/event priority levels."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class ConfidenceLevel(str, Enum):
    """Qualitative confidence levels."""
    CONFIRMED = "confirmed"      # > 0.95
    PROBABLE = "probable"        # 0.75 - 0.95
    POSSIBLE = "possible"        # 0.50 - 0.75
    DOUBTFUL = "doubtful"        # 0.25 - 0.50
    IMPROBABLE = "improbable"    # < 0.25

    @classmethod
    def from_score(cls, score: float) -> "ConfidenceLevel":
        if score > 0.95:
            return cls.CONFIRMED
        elif score > 0.75:
            return cls.PROBABLE
        elif score > 0.50:
            return cls.POSSIBLE
        elif score > 0.25:
            return cls.DOUBTFUL
        else:
            return cls.IMPROBABLE


class CognitivePhase(str, Enum):
    """Phases of the cognitive loop."""
    PERCEIVE = "perceive"
    ORIENT = "orient"
    DECIDE = "decide"
    ACT = "act"
    LEARN = "learn"


# ─── Type Aliases ───────────────────────────────────────────────

EntityId = str
EventId = str
SessionId = str
ModelId = str
ToolId = str
SkillId = str

JSON = Dict[str, Any]
Metadata = Dict[str, Any]
Provenance = List[str]


# ─── Protocols ──────────────────────────────────────────────────

@runtime_checkable
class Serializable(Protocol):
    """Any object that can serialize to dict."""
    def to_dict(self) -> Dict[str, Any]: ...


@runtime_checkable
class Identifiable(Protocol):
    """Any object with a stable identifier."""
    @property
    def id(self) -> str: ...


@runtime_checkable  
class Traceable(Protocol):
    """
    Any object with provenance tracking.

    Provenance is a first-class system property:
    WHY? → WHAT DATA? → WHICH MODEL? → WHAT ASSUMPTIONS?
    → WHAT ALTERNATIVES? → HOW CONFIDENT? → WHO APPROVED?
    → WHAT HAPPENED AFTER?
    """
    @property
    def provenance(self) -> List[str]: ...
    @property
    def confidence(self) -> float: ...


__all__ = [
    "Domain",
    "Priority",
    "ConfidenceLevel",
    "CognitivePhase",
    "EntityId",
    "EventId",
    "SessionId",
    "ModelId",
    "ToolId",
    "SkillId",
    "JSON",
    "Metadata",
    "Provenance",
    "Serializable",
    "Identifiable",
    "Traceable",
]

