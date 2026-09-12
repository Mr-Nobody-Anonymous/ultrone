# Copyright (c) Ultrone Contributors. All rights reserved.
"""Entity Identity, IFF, Classification and Affiliation schemas."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional


class Affiliation(str, Enum):
    FRIEND = "friend"
    HOSTILE = "hostile"
    NEUTRAL = "neutral"
    UNKNOWN = "unknown"
    SUSPECT = "suspect"
    ASSUMED_FRIEND = "assumed_friend"


class OperationalDomain(str, Enum):
    AIR = "air"
    GROUND = "ground"
    MARITIME_SURFACE = "maritime_surface"
    MARITIME_SUBSURFACE = "maritime_subsurface"
    SPACE = "space"
    CYBER = "cyber"
    ELECTROMAGNETIC = "electromagnetic"


@dataclass
class IFFCode:
    """Identification Friend or Foe transponder code."""
    mode_1: Optional[str] = None
    mode_2: Optional[str] = None
    mode_3a: Optional[str] = None
    mode_4: Optional[str] = None
    mode_5: Optional[str] = None
    mode_s: Optional[str] = None


@dataclass
class Identity:
    """Full operational identity of an entity."""
    callsign: str = "UNKNOWN"
    tail_number: Optional[str] = None
    affiliation: Affiliation = Affiliation.UNKNOWN
    domain: OperationalDomain = OperationalDomain.AIR
    iff: Optional[IFFCode] = None
    nationality: str = "UNSPECIFIED"
    aliases: List[str] = field(default_factory=list)
    confidence: float = 1.0
