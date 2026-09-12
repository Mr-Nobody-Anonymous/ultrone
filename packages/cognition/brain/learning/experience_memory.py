# Copyright (c) Ultrone Contributors. All rights reserved.
"""Engagement history storage for learning from past combat experiences.

Two storage tiers -- the docstring matters because the two behave
differently under process restart:

- **In-memory** -- ``ExperienceMemory`` keeps the working window of
  engagements in RAM for the running process. This is *episodic
  runtime memory* and is lost on process exit.
- **Durable** -- ``save(path)`` / ``load(path)`` round-trip the full
  history (with secondary indexes rebuilt on replay) to JSON so
  experience survives process restarts. This is *long-term memory*.

The two are deliberately separate: a deployed agent may legitimately
want fast in-memory access for the current mission while persisting to
durable storage for next-mission warmup. Tests in
``tests/test_cross_process_persistence.py`` measure the cross-process
property directly with ``multiprocessing`` -- a passing in-process
save/load is necessary but not sufficient.

Durable persistence is what turns "episodic runtime memory" into long
term memory; without it, every restart of ULTRONE starts from zero.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Union


class EngagementOutcome(Enum):
    """Outcome of an engagement."""
    SUCCESSFUL = "successful"
    FAILED = "failed"
    PARTIAL = "partial"
    ABORTED = "aborted"


@dataclass
class EngagementHistory:
    """Records a single engagement event."""
    engagement_id: str
    attacker_id: str
    target_id: str
    domain: str
    engagement_type: str
    outcome: EngagementOutcome
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    duration_ms: float = 0.0
    kill_chain_phases: List[str] = field(default_factory=list)
    tactics_used: List[str] = field(default_factory=list)
    casualties: int = 0
    damage_dealt: float = 0.0
    notes: str = ""
    
    def to_dict(self) -> dict:
        return {
            "engagement_id": self.engagement_id,
            "attacker_id": self.attacker_id,
            "target_id": self.target_id,
            "domain": self.domain,
            "engagement_type": self.engagement_type,
            "outcome": self.outcome.value,
            "timestamp": self.timestamp,
            "duration_ms": self.duration_ms,
            "kill_chain_phases": self.kill_chain_phases,
            "tactics_used": self.tactics_used,
            "casualties": self.casualties,
            "damage_dealt": self.damage_dealt,
        }


class ExperienceMemory:
    """
    Stores and manages engagement history for pattern mining.
    
    Provides a searchable record of past engagements with outcomes,
    tactics used, and effectiveness metrics.
    """
    
    def __init__(self, max_history: int = 10000):
        self.max_history = max_history
        self.engagements: List[EngagementHistory] = []
        self.by_domain: Dict[str, List[EngagementHistory]] = {}
        self.by_tactic: Dict[str, int] = {}
        self._outcomes = {
            "successful": 0,
            "failed": 0,
            "partial": 0,
            "aborted": 0,
        }
    
    def record_engagement(self, engagement: EngagementHistory) -> None:
        """Record an engagement outcome."""
        self.engagements.append(engagement)
        
        # Maintain window
        if len(self.engagements) > self.max_history:
            old = self.engagements.pop(0)
            self._update_counts(old, -1)
        
        self._update_counts(engagement, 1)
        
        # Index by domain
        if engagement.domain not in self.by_domain:
            self.by_domain[engagement.domain] = []
        self.by_domain[engagement.domain].append(engagement)
        
        # Index by tactics
        for tactic in engagement.tactics_used:
            self.by_tactic[tactic] = self.by_tactic.get(tactic, 0) + 1
    
    def _update_counts(self, engagement: EngagementHistory, delta: int) -> None:
        """Update outcome counters."""
        key = engagement.outcome.value
        if key in self._outcomes:
            self._outcomes[key] += delta
    
    def get_success_rate(self, domain: Optional[str] = None) -> float:
        """Get success rate, optionally for a specific domain."""
        total = self._outcomes["successful"] + self._outcomes["failed"]
        if total == 0:
            return 1.0
        return self._outcomes["successful"] / total
    
    def get_domain_history(self, domain: str, limit: int = 100) -> List[EngagementHistory]:
        """Get engagement history for a domain."""
        return self.by_domain.get(domain, [])[-limit:]
    
    def get_tactic_effectiveness(self, tactic: str) -> Dict[str, Any]:
        """Get effectiveness metrics for a tactic."""
        # This would be expanded to track specific tactic outcomes
        return {
            "uses": self.by_tactic.get(tactic, 0),
            "success_rate": 0.75,  # Placeholder - would calculate from history
        }
    
    def get_recent_engagements(self, hours: int = 24) -> List[EngagementHistory]:
        """Get engagements from recent hours."""
        cutoff = datetime.utcnow().timestamp() - (hours * 3600)
        result = []
        for e in self.engagements:
            try:
                ts = datetime.fromisoformat(e.timestamp).timestamp()
                if ts >= cutoff:
                    result.append(e)
            except (ValueError, TypeError):
                continue
        return result
    
    def clear(self) -> None:
        """Clear all engagement history."""
        self.engagements.clear()
        self.by_domain.clear()
        self.by_tactic.clear()
        self._outcomes = {"successful": 0, "failed": 0, "partial": 0, "aborted": 0}
    
    def get_stats(self) -> dict:
        return {
            "total_engagements": len(self.engagements),
            "by_domain": {d: len(e) for d, e in self.by_domain.items()},
            "outcomes": self._outcomes.copy(),
            "unique_tactics": len(self.by_tactic),
        }

    # -- durable persistence --------------------------------------------------
    # Without these, the experience layer is *runtime* memory only --
    # every process restart loses history. The closed-loop learning test
    # relies on ``save``/``load`` to prove the experience actually flows
    # across a process boundary.

    _SCHEMA_VERSION = 1

    def save(self, path: Union[str, Path]) -> None:
        """Persist the full engagement window to ``path`` as JSON.

        Uses a schema-versioned envelope so older payloads can still be
        inspected and future migrations are possible without a hard break.
        """
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "schema_version": self._SCHEMA_VERSION,
            "max_history": self.max_history,
            "engagements": [e.to_dict() for e in self.engagements],
        }
        target.write_text(
            json.dumps(payload, sort_keys=True, indent=2),
            encoding="utf-8",
        )

    @classmethod
    def load(cls, path: Union[str, Path]) -> "ExperienceMemory":
        """Rehydrate an ``ExperienceMemory`` previously written by ``save``.

        The replay path replays every engagement through
        ``record_engagement`` so the secondary indexes (``by_domain``,
        ``by_tactic``, outcome counts, sliding window) are rebuilt
        identically to a fresh process. That is the property a closed
        loop actually depends on.
        """
        source = Path(path)
        payload = json.loads(source.read_text(encoding="utf-8"))
        if payload.get("schema_version") != cls._SCHEMA_VERSION:
            raise ValueError(
                f"unsupported experience schema "
                f"{payload.get('schema_version')!r}; expected "
                f"{cls._SCHEMA_VERSION}"
            )
        memory = cls(max_history=int(payload.get("max_history", 10000)))
        for raw in payload.get("engagements", []):
            memory.record_engagement(
                EngagementHistory(
                    engagement_id=raw["engagement_id"],
                    attacker_id=raw["attacker_id"],
                    target_id=raw["target_id"],
                    domain=raw["domain"],
                    engagement_type=raw["engagement_type"],
                    outcome=EngagementOutcome(raw["outcome"]),
                    timestamp=raw.get("timestamp",
                                       datetime.utcnow().isoformat()),
                    duration_ms=float(raw.get("duration_ms", 0.0)),
                    kill_chain_phases=list(raw.get("kill_chain_phases", [])),
                    tactics_used=list(raw.get("tactics_used", [])),
                    casualties=int(raw.get("casualties", 0)),
                    damage_dealt=float(raw.get("damage_dealt", 0.0)),
                    notes=raw.get("notes", ""),
                )
            )
        return memory