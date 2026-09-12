# Copyright (c) Ultrone Contributors. All rights reserved.
"""Independent safety enforcement between planning and execution.

The safety gate is deliberately *independent* of the planner: it evaluates
a proposed :class:`~core.contracts.ActionOrder` against constraints using
only the fused world estimate and asset state read directly from the
environment. The proposing intelligence cannot certify its own proposal.
"""

from __future__ import annotations

import math
from typing import List, Sequence, Set

from core.contracts import (
    ActionOrder,
    AssetSnapshot,
    SafetyRuleResult,
    SafetyVerdict,
    WorldEstimate,
)


class SafetyConfig:
    """Thresholds and policy knobs for the safety gate."""

    def __init__(
        self,
        min_engagement_confidence: float = 0.45,
        min_fuel_reserve: float = 0.05,
        blacklisted_actions: Sequence[str] = (),
        require_positive_ammo_for_strike: bool = True,
    ) -> None:
        self.min_engagement_confidence = min_engagement_confidence
        self.min_fuel_reserve = min_fuel_reserve
        self.blacklisted_actions: Set[str] = {a.lower() for a in blacklisted_actions}
        self.require_positive_ammo_for_strike = require_positive_ammo_for_strike


class SafetyGate:
    """Validates proposed orders before execution. Pure function of inputs."""

    RULE_TARGET_PRESENT = "R1_TARGET_PRESENT"
    RULE_CONFIDENCE = "R2_ENGAGEMENT_CONFIDENCE"
    RULE_AMMO = "R3_AMMO_AVAILABLE"
    RULE_RANGE = "R4_ENGAGEMENT_RANGE"
    RULE_FUEL = "R5_FUEL_RESERVE"
    RULE_BLACKLIST = "R6_ACTION_BLACKLIST"

    KINETIC_ACTIONS = frozenset({"strike", "engage", "assassinate"})

    def __init__(self, config: SafetyConfig | None = None) -> None:
        self.config = config or SafetyConfig()

    def evaluate(
        self,
        order: ActionOrder,
        estimate: WorldEstimate,
        asset: AssetSnapshot,
    ) -> SafetyVerdict:
        """Run all rules; approve only if every rule passes."""
        results: List[SafetyRuleResult] = []
        cfg = self.config
        kinetic = order.action.lower() in self.KINETIC_ACTIONS

        # R1: a concrete target must exist for directed orders.
        if order.target is None:
            results.append(SafetyRuleResult(
                self.RULE_TARGET_PRESENT, False,
                f"action '{order.action}' has no target",
            ))
        else:
            results.append(SafetyRuleResult(
                self.RULE_TARGET_PRESENT, True, "target present",
            ))

        # R2: kinetic engagement requires sufficient belief confidence.
        if kinetic:
            conf = estimate.primary_target_confidence
            passed = conf >= cfg.min_engagement_confidence
            results.append(SafetyRuleResult(
                self.RULE_CONFIDENCE, passed,
                f"confidence {conf:.2f} vs required "
                f"{cfg.min_engagement_confidence:.2f}",
            ))
        else:
            results.append(SafetyRuleResult(
                self.RULE_CONFIDENCE, True, "not applicable (non-kinetic)",
            ))

        # R3: strike requires ammunition.
        if kinetic and cfg.require_positive_ammo_for_strike:
            passed = asset.ammo > 0
            results.append(SafetyRuleResult(
                self.RULE_AMMO, passed, f"ammo={asset.ammo}",
            ))
        else:
            results.append(SafetyRuleResult(
                self.RULE_AMMO, True, "not applicable",
            ))

        # R4: believed target must be inside engagement range.
        if kinetic and order.target is not None and asset.position is not None:
            dist = math.dist(asset.position, order.target)
            passed = dist <= asset.range
            results.append(SafetyRuleResult(
                self.RULE_RANGE, passed,
                f"believed distance {dist:.1f} vs range {asset.range:.1f}",
            ))
        else:
            results.append(SafetyRuleResult(
                self.RULE_RANGE, True, "not applicable",
            ))

        # R5: acting asset must retain fuel reserve.
        passed = asset.fuel > cfg.min_fuel_reserve
        results.append(SafetyRuleResult(
            self.RULE_FUEL, passed,
            f"fuel {asset.fuel:.2f} vs reserve {cfg.min_fuel_reserve:.2f}",
        ))

        # R6: explicitly blacklisted actions are always rejected.
        passed = order.action.lower() not in cfg.blacklisted_actions
        results.append(SafetyRuleResult(
            self.RULE_BLACKLIST, passed,
            "blacklisted" if not passed else "permitted",
        ))

        failed = [r.rule_id for r in results if not r.passed]
        return SafetyVerdict(
            approved=not failed,
            reason="approved" if not failed else f"rejected by {failed}",
            rule_results=results,
        )
