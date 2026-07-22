# Copyright (c) Ultrone Contributors. All rights reserved.
"""Operational-level mission planning and force allocation."""

import logging
from typing import Dict, List, Optional
from dataclasses import dataclass
import uuid

from ...data.entities import Unit, DomainType

logger = logging.getLogger("Ultrone.Brain.Strategy.OperationalPlanner")


@dataclass
class Mission:
    """A mission assigned to units."""
    mission_id: str
    name: str
    description: str
    domain: DomainType
    objective: str
    assigned_units: List[str]
    priority: int = 1  # 1=high, 5=low
    start_time: str = ""
    end_time: str = ""
    
    def to_dict(self) -> dict:
        return {
            "mission_id": self.mission_id,
            "name": self.name,
            "description": self.description,
            "domain": self.domain.value,
            "objective": self.objective,
            "assigned_units": self.assigned_units,
            "priority": self.priority,
        }


class OperationalPlanner:
    """
    Mission-level force allocation and planning.
    
    Creates and manages missions for achieving tactical objectives.
    """
    
    def __init__(self):
        self.missions: Dict[str, Mission] = {}
    
    def create_mission(
        self,
        name: str,
        objective: str,
        domain: DomainType,
        description: str = "",
        priority: int = 1,
    ) -> Mission:
        """Create a new mission."""
        mission = Mission(
            mission_id=f"MSN-{uuid.uuid4().hex[:6].upper()}",
            name=name,
            description=description,
            domain=domain,
            objective=objective,
            assigned_units=[],
            priority=priority,
        )
        self.missions[mission.mission_id] = mission
        return mission
    
    def allocate_units(
        self,
        mission_id: str,
        units: List[Unit],
        required_count: int = 1,
    ) -> int:
        """Allocate units to a mission."""
        mission = self.missions.get(mission_id)
        if not mission:
            return 0
        
        available = [u for u in units if u.is_operational() and u.domain == mission.domain]
        
        for unit in available[:required_count]:
            if unit.unit_id not in mission.assigned_units:
                mission.assigned_units.append(unit.unit_id)
        
        return len(mission.assigned_units)
    
    def get_missions_for_domain(self, domain: DomainType) -> List[Mission]:
        """Get active missions for a domain."""
        return [m for m in self.missions.values() if m.domain == domain]
    
    def get_priority_missions(self, max_priority: int = 2) -> List[Mission]:
        """Get high-priority missions."""
        return [m for m in self.missions.values() if m.priority <= max_priority]
    
    def complete_mission(self, mission_id: str) -> Optional[Mission]:
        """Mark a mission as complete."""
        mission = self.missions.get(mission_id)
        if mission:
            return self.missions.pop(mission_id)
        return None
    
    def get_stats(self) -> dict:
        return {
            "active_missions": len(self.missions),
            "by_domain": {
                d.value: len(self.get_missions_for_domain(d))
                for d in DomainType
            },
            "high_priority": len(self.get_priority_missions()),
        }