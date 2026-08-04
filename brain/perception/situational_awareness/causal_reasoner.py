# Copyright (c) Ultrone Contributors. All rights reserved.
"""Causal reasoning over entity relationships and events.

Builds and maintains a causal graph linking events and entity states.
Supports:

* causal link inference from temporal precedence
* causal strength estimation
* causal path discovery
* counterfactual reasoning
* causal graph queries
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Set, Tuple

from .types import utc_now

__all__ = [
    "CausalLink",
    "CausalReasoner",
    "CausalReasonerConfig",
]


@dataclass
class CausalLink:
    """A directed causal relationship between two events or entities."""

    cause_id: str
    effect_id: str
    strength: float = 0.5
    confidence: float = 0.5
    temporal_lag: float = 0.0
    evidence_count: int = 1
    first_seen: datetime = field(default_factory=utc_now)
    last_updated: datetime = field(default_factory=utc_now)
    metadata: Dict[str, Any] = field(default_factory=dict)


class CausalReasonerConfig:
    """Configuration for the causal reasoner."""

    def __init__(
        self,
        *,
        min_evidence: int = 2,
        strength_threshold: float = 0.3,
        max_lag_seconds: float = 60.0,
    ) -> None:
        self.min_evidence = min_evidence
        self.strength_threshold = strength_threshold
        self.max_lag_seconds = max_lag_seconds


class CausalReasoner:
    """Infers and maintains causal relationships between events."""

    def __init__(self, *, config: Optional[CausalReasonerConfig] = None) -> None:
        self._config = config or CausalReasonerConfig()
        self._links: Dict[str, CausalLink] = {}
        self._event_times: Dict[str, List[datetime]] = {}

    def record_event(self, event_id: str, timestamp: Optional[datetime] = None) -> None:
        """Record the occurrence time of an event."""
        timestamp = timestamp or utc_now()
        self._event_times.setdefault(event_id, []).append(timestamp)

    def infer_link(
        self, cause_id: str, effect_id: str, *, lag_seconds: float = 0.0
    ) -> Optional[CausalLink]:
        """Infer a causal link from temporal precedence evidence."""
        cause_times = self._event_times.get(cause_id, [])
        effect_times = self._event_times.get(effect_id, [])
        if not cause_times or not effect_times:
            return None

        # Count how many times a cause precedes an effect within the lag window.
        evidence = 0
        for ct in cause_times:
            for et in effect_times:
                delta = (et - ct).total_seconds()
                if 0 <= delta <= self._config.max_lag_seconds:
                    evidence += 1

        if evidence < self._config.min_evidence:
            return None

        strength = min(1.0, evidence / max(len(cause_times), 1))
        key = f"{cause_id}->{effect_id}"
        link = self._links.get(key)
        if link is None:
            link = CausalLink(
                cause_id=cause_id,
                effect_id=effect_id,
                strength=strength,
                temporal_lag=lag_seconds,
                evidence_count=evidence,
            )
            self._links[key] = link
        else:
            link.strength = 0.7 * link.strength + 0.3 * strength
            link.evidence_count += evidence
            link.last_updated = utc_now()

        return link

    def add_link(
        self,
        cause_id: str,
        effect_id: str,
        *,
        strength: float = 0.5,
        confidence: float = 0.5,
        temporal_lag: float = 0.0,
    ) -> CausalLink:
        """Explicitly add a causal link."""
        key = f"{cause_id}->{effect_id}"
        link = CausalLink(
            cause_id=cause_id,
            effect_id=effect_id,
            strength=strength,
            confidence=confidence,
            temporal_lag=temporal_lag,
        )
        self._links[key] = link
        return link

    def get_link(self, cause_id: str, effect_id: str) -> Optional[CausalLink]:
        return self._links.get(f"{cause_id}->{effect_id}")

    def causes_of(self, effect_id: str) -> List[CausalLink]:
        return [
            link
            for link in self._links.values()
            if link.effect_id == effect_id
            and link.strength >= self._config.strength_threshold
        ]

    def effects_of(self, cause_id: str) -> List[CausalLink]:
        return [
            link
            for link in self._links.values()
            if link.cause_id == cause_id
            and link.strength >= self._config.strength_threshold
        ]

    def causal_path(
        self, start_id: str, end_id: str, max_depth: int = 5
    ) -> List[CausalLink]:
        """Find a causal path from start to end via BFS."""
        from collections import deque

        queue: deque[Tuple[str, List[CausalLink]]] = deque([(start_id, [])])
        visited: Set[str] = {start_id}

        while queue:
            current, path = queue.popleft()
            if len(path) >= max_depth:
                continue
            for link in self.effects_of(current):
                if link.effect_id == end_id:
                    return path + [link]
                if link.effect_id not in visited:
                    visited.add(link.effect_id)
                    queue.append((link.effect_id, path + [link]))
        return []

    def counterfactual(
        self, effect_id: str, removed_cause_id: str
    ) -> float:
        """Estimate the probability of an effect without a given cause."""
        causes = self.causes_of(effect_id)
        if not causes:
            return 0.0
        total_strength = sum(c.strength for c in causes)
        removed = self.get_link(removed_cause_id, effect_id)
        if removed is None:
            return 1.0
        remaining = total_strength - removed.strength
        return max(0.0, min(1.0, remaining / max(total_strength, 1e-12)))

    def link_count(self) -> int:
        return len(self._links)

    def all_links(self) -> List[CausalLink]:
        return list(self._links.values())

    def clear(self) -> None:
        self._links.clear()
        self._event_times.clear()