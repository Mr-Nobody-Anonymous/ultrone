# Copyright (c) Ultrone Contributors. All rights reserved.
"""Core tactical engine - the assess → COA → select → decompose → orders loop."""

from __future__ import annotations

import logging
import random
import uuid
from typing import Dict, List, Optional, Any, TYPE_CHECKING
from dataclasses import dataclass

logger = logging.getLogger("Ultrone.Brain.Reasoning.TacticalEngine")

if TYPE_CHECKING:
    from brain.perception.situational_awareness import SituationalAwareness, COPContact
    from brain.reasoning.course_of_action import COAGenerator, CourseOfAction
    from brain.reasoning.kill_chain import KillChain, KillChainPhase
    from brain.reasoning.resource_allocator import ResourceAllocator, Allocation
    from config.doctrine_presets import DoctrinePreset
    from data.entities import Unit, Contact, DomainType


@dataclass
class TacticalAssessment:
    """Result of tactical assessment."""
    target_contact_id: str
    threat_score: float
    selected_coa: Optional[Any]  # CourseOfAction
    assigned_assets: List[Any]  # Allocation
    estimated_success: float

    def to_dict(self) -> dict:
        return {
            "target_contact_id": self.target_contact_id,
            "threat_score": self.threat_score,
            "selected_coa": self.selected_coa.name if self.selected_coa else None,
            "assigned_assets": len(self.assigned_assets),
            "estimated_success": self.estimated_success,
        }


class TacticalEngine:
    """
    Core tactical loop.

    1. Assess threats from COP
    2. Generate COAs for high-priority targets
    3. Select best COA
    4. Decompose into orders
    5. Dispatch to assets
    """

    def __init__(self, doctrine: Optional[Any] = None) -> None:
        # Late imports to avoid circular dependencies
        from brain.perception.situational_awareness import SituationalAwareness
        from brain.reasoning.course_of_action import COAGenerator
        from brain.reasoning.resource_allocator import ResourceAllocator
        from brain.reasoning.kill_chain import KillChain
        
        self.situational_awareness: SituationalAwareness = SituationalAwareness()
        self.coa_generator: COAGenerator = COAGenerator()
        self.resource_allocator: ResourceAllocator = ResourceAllocator()
        self.kill_chain: KillChain = KillChain()
        self.doctrine = doctrine
        self.assessments: List[TacticalAssessment] = []
        
        # Search & Planning integration (Phase 1)
        # Pluggable planner; if None, falls back to COAGenerator.
        # Set via set_planner() to use MCTS, AStar, HTN, etc.
        self._planner: Optional[Any] = None

    def assess(self, units: Any, feeds: Any, min_threat: float = 0.5) -> Any:
        """Assess current situation and return threatening contacts."""
        # Update COP
        self.situational_awareness.update(feeds, units)

        # Get threatening contacts
        from data.entities import ThreatLevel
        threatening = self.situational_awareness.get_threatening_contacts(
            ThreatLevel.HIGH
        )

        return threatening

    def decide(self, threatening_contacts: Any, units: Any) -> List[TacticalAssessment]:
        """Generate COAs and assign assets for threats."""
        self.assessments.clear()

        for contact in threatening_contacts:
            # Generate COAs
            target_info = {
                "type": contact.contact.threat_level.name,
                "domain": contact.contact.domain.value,
            }
            coas = self.coa_generator.generate(target_info)

            # Select best COA
            selected = self.coa_generator.select_best(coas)

            # Allocate resources
            contacts_list = [contact.contact]
            allocations = self.resource_allocator.allocate(units, contacts_list)

            # Calculate success estimate
            success = 0.0
            if selected:
                success = selected.get_total_score()
            if allocations:
                success *= sum(a.expected_effect for a in allocations) / len(allocations)

            assessment = TacticalAssessment(
                target_contact_id=contact.contact.contact_id,
                threat_score=contact.threat_score.score if contact.threat_score else 0,
                selected_coa=selected,
                assigned_assets=allocations,
                estimated_success=min(1.0, success),
            )
            self.assessments.append(assessment)

            # Start kill chain
            if selected and allocations:
                kc = self.kill_chain.start(contact.contact.contact_id)

        return self.assessments

    def get_orders(self) -> List[Dict[str, Any]]:
        """Get orders for assets based on assessments."""
        orders = []
        for assessment in self.assessments:
            for alloc in assessment.assigned_assets:
                orders.append({
                    "order_id": f"ORD-{uuid.uuid4().hex[:6].upper()}",
                    "unit_id": alloc.unit_id,
                    "contact_id": alloc.contact_id,
                    "weapon": alloc.weapon_type,
                    "action": "engage",
                    "coa": assessment.selected_coa.name if assessment.selected_coa else "direct",
                })
        return orders

    def execute(self, units: Dict[str, Any]) -> Dict[str, Any]:
        """Execute orders against units."""
        orders = self.get_orders()
        results = {"executed": 0, "failed": 0, "details": []}

        for order in orders:
            unit = units.get(order["unit_id"])
            if unit and unit.is_operational():
                # Simulate engagement
                success = random.random() < 0.8
                results["executed"] += 1
                results["details"].append({
                    "order_id": order["order_id"],
                    "unit_id": order["unit_id"],
                    "success": success,
                })
            else:
                results["failed"] += 1

        return results

    def set_planner(self, planner: Any) -> None:
        """Inject a search planner (MCTS, AStar, HTN, etc.)

        The planner must implement the ``Planner`` interface from
        ``brain.reasoning.search.base``.

        When a planner is set, the engine will use it to generate
        COAs instead of the default COAGenerator.
        """
        self._planner = planner
        logger.info("TacticalEngine planner set to %s", type(planner).__name__)

    def get_stats(self) -> dict:
        stats = {
            "active_assessments": len(self.assessments),
            "cop_stats": self.situational_awareness.get_stats(),
            "kill_chains": self.kill_chain.get_stats(),
        }
        if self._planner:
            stats["planner_stats"] = self._planner.get_stats()
        return stats
