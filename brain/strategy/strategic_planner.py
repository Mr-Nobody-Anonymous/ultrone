# Copyright (c) Ultrone Contributors. All rights reserved.
"""Strategic-level campaign planning and objective management."""

import logging
from typing import Dict, List, Optional
from dataclasses import dataclass, field
from datetime import datetime
import uuid

logger = logging.getLogger("Ultrone.Brain.Strategy.StrategicPlanner")


@dataclass
class StrategicObjective:
    """A high-level campaign objective."""
    objective_id: str
    name: str
    description: str
    priority: int
    status: str = "planned"  # planned, active, completed, failed
    sub_objectives: List[str] = field(default_factory=list)
    start_time: Optional[str] = None
    completion_time: Optional[str] = None
    
    def to_dict(self) -> dict:
        return {
            "objective_id": self.objective_id,
            "name": self.name,
            "description": self.description,
            "priority": self.priority,
            "status": self.status,
            "sub_objectives_count": len(self.sub_objectives),
        }


class StrategicPlanner:
    """
    Campaign-level objective planning.
    
    Manages high-level objectives and decomposes them into
    operational missions.
    """
    
    def __init__(self):
        self.objectives: Dict[str, StrategicObjective] = {}
        self.active_objectives: List[str] = []
    
    def add_objective(
        self,
        name: str,
        description: str,
        priority: int = 1,
    ) -> StrategicObjective:
        """Add a strategic objective."""
        obj = StrategicObjective(
            objective_id=f"OBJ-{uuid.uuid4().hex[:6].upper()}",
            name=name,
            description=description,
            priority=priority,
            status="planned",
        )
        self.objectives[obj.objective_id] = obj
        return obj
    
    def activate_objective(self, objective_id: str) -> Optional[StrategicObjective]:
        """Activate an objective."""
        obj = self.objectives.get(objective_id)
        if obj:
            obj.status = "active"
            obj.start_time = datetime.utcnow().isoformat()
            if objective_id not in self.active_objectives:
                self.active_objectives.append(objective_id)
        return obj
    
    def add_sub_objective(self, objective_id: str, sub_obj_id: str) -> bool:
        """Add a sub-objective to an objective."""
        obj = self.objectives.get(objective_id)
        if obj:
            obj.sub_objectives.append(sub_obj_id)
            return True
        return False
    
    def complete_objective(self, objective_id: str) -> Optional[StrategicObjective]:
        """Mark objective as complete."""
        obj = self.objectives.get(objective_id)
        if obj:
            obj.status = "completed"
            obj.completion_time = datetime.utcnow().isoformat()
            if objective_id in self.active_objectives:
                self.active_objectives.remove(objective_id)
        return obj
    
    def get_active(self) -> List[StrategicObjective]:
        """Get active objectives."""
        return [self.objectives[oid] for oid in self.active_objectives]
    
    def decompose_to_missions(self, objective_id: str) -> List[Dict]:
        """Decompose objective into missions for operational planner."""
        obj = self.objectives.get(objective_id)
        if not obj:
            return []
        
        # Generate missions based on objective
        missions = []
        
        if "air" in obj.description.lower():
            missions.append({
                "name": f"Air Campaign: {obj.name}",
                "objective": obj.objective_id,
                "domain": "air",
            })
        
        if "naval" in obj.description.lower() or "sea" in obj.description.lower():
            missions.append({
                "name": f"Naval Campaign: {obj.name}",
                "objective": obj.objective_id,
                "domain": "sea",
            })
        
        if "cyber" in obj.description.lower():
            missions.append({
                "name": f"Cyber Campaign: {obj.name}",
                "objective": obj.objective_id,
                "domain": "cyber",
            })
        
        return missions
    
    def get_stats(self) -> dict:
        return {
            "total_objectives": len(self.objectives),
            "active": len(self.active_objectives),
            "completed": len([o for o in self.objectives.values() if o.status == "completed"]),
        }