# Copyright (c) Ultrone Contributors. All rights reserved.
"""Resource allocation - matching assets to targets based on capabilities."""

from __future__ import annotations

import logging
from typing import Dict, List, Optional, Tuple, TYPE_CHECKING
from dataclasses import dataclass
import random

logger = logging.getLogger("Ultrone.Brain.Reasoning.ResourceAllocator")

if TYPE_CHECKING:
    from ...data.entities import Unit, Contact, DomainType


@dataclass
class Allocation:
    """Assignment of an asset to a target."""
    unit_id: str
    contact_id: str
    weapon_type: str
    expected_effect: float  # 0.0-1.0 probability of success

    def to_dict(self) -> dict:
        return {
            "unit_id": self.unit_id,
            "contact_id": self.contact_id,
            "weapon_type": self.weapon_type,
            "expected_effect": self.expected_effect,
        }


class ResourceAllocator:
    """
    Matches asset capabilities to target vulnerabilities.

    Chooses the best available units to engage each target
    based on weapon effectiveness, range, and availability.
    """

    # Effectiveness matrix: weapon type vs target type
    EFFECTIVENESS_MATRIX = {
        "AIM_120_AMRAAM": {"fighter": 0.95, "drone": 0.85, "missile": 0.98, "bomber": 0.99},
        "AIM_9X_Sidewinder": {"fighter": 0.9, "drone": 0.75, "missile": 0.85},
        "JDAM": {"tank": 0.95, "artillery": 0.85, "bomber": 0.99},
        "hellfire": {"tank": 0.85, "infantry": 0.9, "mobile_missile": 0.8},
        "naval_gun": {"vessel": 0.7, "submarine": 0.4},
        "torpedo": {"submarine": 0.95, "vessel": 0.85},
        "cyber_attack": {"cyber": 0.9, "system": 0.85},
        "satellite_laser": {"satellite": 0.99, "vessel": 0.7, "vehicle": 0.8},
    }

    def __init__(self):
        self.allocations: List[Allocation] = []

    def allocate(
        self,
        available_units: Any,
        contacts: Any,
        max_allocations: int = 10,
    ) -> List[Allocation]:
        """
        Allocate assets to targets.

        Returns list of allocations sorted by expected effect.
        """
        self.allocations.clear()

        for contact in contacts:
            best_unit = self._find_best_unit(contact, available_units)
            if best_unit:
                weapon = self._select_weapon(best_unit, contact)
                effect = self._calculate_effect(weapon, contact)

                allocation = Allocation(
                    unit_id=best_unit.unit_id,
                    contact_id=contact.contact_id,
                    weapon_type=weapon,
                    expected_effect=effect,
                )
                self.allocations.append(allocation)

        # Sort by effectiveness
        self.allocations.sort(key=lambda a: a.expected_effect, reverse=True)

        return self.allocations[:max_allocations]

    def _find_best_unit(self, contact: Any, units: Any) -> Optional[Any]:
        """Find the best available unit for a contact."""
        candidates = []

        for unit in units:
            if not unit.is_operational():
                continue
            if unit.team != "blue":
                continue  # Only allocate blue units

            # Check domain match or capability match
            if unit.domain == contact.domain:
                candidates.append(unit)
            elif unit.domain.value in ["air", "land", "sea"] and contact.domain in [DomainType.AIR, DomainType.LAND, DomainType.SEA]:
                candidates.append(unit)

        if not candidates:
            return None

        # Prefer units with highest ammunition and health
        return max(candidates, key=lambda u: u.ammunition * u.health)

    def _select_weapon(self, unit: Any, contact: Any) -> str:
        """Select appropriate weapon for engagement."""
        # Base weapon selection on unit type
        if "fighter" in unit.unit_type or "drone" in unit.unit_type:
            weapons = ["AIM_120_AMRAAM", "AIM_9X_Sidewinder"]
        elif "tank" in unit.unit_type:
            weapons = ["cannon", "hellfire"]
        elif "vessel" in unit.unit_type:
            weapons = ["naval_gun", "torpedo", "missile"]
        elif "submarine" in unit.unit_type:
            weapons = ["torpedo"]
        elif "cyber" in unit.unit_type:
            weapons = ["cyber_attack"]
        elif "satellite" in unit.unit_type:
            weapons = ["satellite_laser"]
        else:
            weapons = ["generic_weapon"]

        return random.choice(weapons) if weapons else "generic_weapon"

    def _calculate_effect(self, weapon: str, contact: Any) -> float:
        """Calculate expected effect of weapon against contact."""
        target_type = "fighter"  # Simplified

        if contact.domain == DomainType.AIR:
            target_type = "fighter"
        elif contact.domain == DomainType.LAND:
            target_type = "tank"
        elif contact.domain == DomainType.SEA:
            target_type = "vessel"

        effect = self.EFFECTIVENESS_MATRIX.get(weapon, {}).get(target_type, 0.5)

        # Adjust for confidence
        effect *= contact.confidence

        # Adjust for threat level (higher threat = more dangerous to us = easier to kill)
        threat_multiplier = {
            "imminent": 1.2,
            "critical": 1.1,
            "high": 1.0,
            "medium": 0.9,
            "low": 0.8,
            "unknown": 0.7,
        }.get(contact.threat_level.name.lower(), 0.7)

        return min(1.0, effect * threat_multiplier)

    def get_stats(self) -> dict:
        return {
            "active_allocations": len(self.allocations),
            "weapons_considered": len(self.EFFECTIVENESS_MATRIX),
        }