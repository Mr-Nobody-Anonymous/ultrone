# Copyright (c) Ultrone Contributors. All rights reserved.
"""Canonical end-to-end data contracts for the ULTRONE decision pipeline.

These types are the authoritative interface between pipeline stages:

    Observation -> SensorReadings -> WorldEstimate -> candidate COAs
        -> ActionOrder -> SafetyVerdict -> execution outcome
        -> DecisionTrace (immutable provenance record)
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple


def new_id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:12]}"


@dataclass
class Observation:
    """Canonical wrapper around a raw environment observation."""
    tick: int
    red_force: Dict[str, Any]
    blue_assets: Dict[str, List[Dict[str, Any]]]
    supply_nodes: Dict[str, Dict[str, Any]]
    raw: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_env(cls, obs: Dict[str, Any], tick: int) -> "Observation":
        return cls(
            tick=tick,
            red_force=dict(obs.get("red_force") or {}),
            blue_assets={
                k: [dict(a) for a in v]
                for k, v in (obs.get("blue_assets") or {}).items()
            },
            supply_nodes={k: dict(v) for k, v in (obs.get("supply_nodes") or {}).items()},
            raw=obs,
        )

    @property
    def true_red_position(self) -> Optional[Tuple[float, float]]:
        pos = self.red_force.get("position")
        return tuple(pos) if pos else None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "tick": self.tick,
            "red_force": self.red_force,
            "blue_assets": self.blue_assets,
            "supply_nodes": self.supply_nodes,
        }


@dataclass
class SensorRecord:
    """One sensor emission attempt, including honest dropouts."""
    feed_id: str
    sensor_type: str
    position: Tuple[float, float, float]
    confidence: float
    dropped: bool = False


@dataclass
class WorldEstimate:
    """The system's *belief* about the world - never ground truth."""
    contacts: List[Dict[str, Any]]
    primary_target_position: Optional[Tuple[float, float]]
    primary_target_confidence: float
    n_feeds_generated: int
    n_feeds_received: int

    @property
    def uncertainty(self) -> float:
        return max(0.0, 1.0 - self.primary_target_confidence)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "contacts": self.contacts,
            "primary_target_position": self.primary_target_position,
            "primary_target_confidence": self.primary_target_confidence,
            "uncertainty": self.uncertainty,
            "n_feeds_generated": self.n_feeds_generated,
            "n_feeds_received": self.n_feeds_received,
        }


@dataclass(frozen=True)
class ActionOrder:
    """A single executable order derived from an approved COA."""
    action: str
    asset_type: str
    target: Optional[Tuple[float, float]]
    source_coa_id: str

    def to_env_action(self) -> Dict[str, Any]:
        return {
            "action": self.action,
            "asset_type": self.asset_type,
            "target": self.target,
        }


@dataclass(frozen=True)
class AssetSnapshot:
    """Asset state read directly from the environment (not from the planner)."""
    asset_type: str
    position: Optional[Tuple[float, float]]
    fuel: float = 1.0
    ammo: int = 0
    range: float = 9999.0


@dataclass(frozen=True)
class SafetyRuleResult:
    rule_id: str
    passed: bool
    detail: str


@dataclass
class SafetyVerdict:
    approved: bool
    reason: str
    rule_results: List[SafetyRuleResult] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "approved": self.approved,
            "reason": self.reason,
            "rules": [
                {"rule_id": r.rule_id, "passed": r.passed, "detail": r.detail}
                for r in self.rule_results
            ],
        }


@dataclass
class DecisionTrace:
    """Immutable provenance record for one decision cycle.

    Answers: what did ULTRONE sense, believe, consider, choose, execute,
    and what happened - for this specific decision ID.
    """
    decision_id: str
    episode_id: str
    tick: int
    sensing: Dict[str, Any] = field(default_factory=dict)
    perception: Dict[str, Any] = field(default_factory=dict)
    world_state: Dict[str, Any] = field(default_factory=dict)
    planning: Dict[str, Any] = field(default_factory=dict)
    safety: Dict[str, Any] = field(default_factory=dict)
    execution: Dict[str, Any] = field(default_factory=dict)
    outcome: Dict[str, Any] = field(default_factory=dict)

    def finalize(self, order: Optional[ActionOrder]) -> "DecisionTrace":
        """Seal the trace; returns self for chaining. Mutates once at creation end."""
        self.execution["order"] = order.to_env_action() if order else None
        return self

    def to_dict(self) -> Dict[str, Any]:
        return {
            "decision_id": self.decision_id,
            "episode_id": self.episode_id,
            "tick": self.tick,
            "sensing": self.sensing,
            "perception": self.perception,
            "world_state": self.world_state,
            "planning": self.planning,
            "safety": self.safety,
            "execution": self.execution,
            "outcome": self.outcome,
        }


@dataclass
class StepResult:
    """Result of one full pipeline cycle."""
    trace: DecisionTrace
    order: Optional[ActionOrder]
    verdict: SafetyVerdict
    reward: float
    done: bool
    info: Dict[str, Any]
