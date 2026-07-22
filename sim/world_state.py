# Copyright (c) Ultrone Contributors. All rights reserved.
"""Single source of truth for all entities, contacts, and world state."""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional

from ..data.entities import Unit, Contact, Formation, DomainType
from ..data.terrain import Terrain

logger = logging.getLogger("Ultrone.Sim.WorldState")


@dataclass
class KillChainTracker:
    """Tracks kill chain progress for engagements."""
    target_id: str
    phase: str  # find, fix, track, target, engage, assess
    started_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    phase_history: List[str] = field(default_factory=list)
    
    def advance_phase(self, new_phase: str) -> None:
        self.phase = new_phase
        self.phase_history.append(f"{datetime.utcnow().isoformat()}:{new_phase}")
    
    def get_progress(self) -> float:
        phases = ["find", "fix", "track", "target", "engage", "assess"]
        try:
            return (phases.index(self.phase) + 1) / len(phases)
        except ValueError:
            return 0.0


class WorldState:
    """
    Single source of truth for the battlefield simulation.
    
    Maintains all entities, contacts, terrain, and state transitions.
    """
    
    def __init__(self, terrain: Optional[Terrain] = None):
        self.terrain = terrain
        self.units: Dict[str, Unit] = {}  # unit_id -> Unit
        self.contacts: Dict[str, Contact] = {}  # contact_id -> Contact
        self.formations: Dict[str, Formation] = {}  # formation_id -> Formation
        self.kill_chains: Dict[str, KillChainTracker] = {}  # target_id -> tracker
        self.blue_force_count = 0
        self.red_force_count = 0
        self.neutral_count = 0
        self.tick_count = 0
    
    def add_unit(self, unit: Unit) -> None:
        """Add a unit to the world state."""
        self.units[unit.unit_id] = unit
        if unit.team == "blue":
            self.blue_force_count += 1
        elif unit.team == "red":
            self.red_force_count += 1
        else:
            self.neutral_count += 1
        logger.debug(f"Added unit {unit.unit_id} to {unit.team} team")
    
    def remove_unit(self, unit_id: str) -> Optional[Unit]:
        """Remove a unit from the world state."""
        unit = self.units.pop(unit_id, None)
        if unit:
            if unit.team == "blue":
                self.blue_force_count = max(0, self.blue_force_count - 1)
            elif unit.team == "red":
                self.red_force_count = max(0, self.red_force_count - 1)
            else:
                self.neutral_count = max(0, self.neutral_count - 1)
        return unit
    
    def add_contact(self, contact: Contact) -> None:
        """Add a detected contact."""
        self.contacts[contact.contact_id] = contact
        logger.debug(f"Added contact {contact.contact_id}")
    
    def remove_contact(self, contact_id: str) -> Optional[Contact]:
        """Remove a contact (e.g., after identification)."""
        return self.contacts.pop(contact_id, None)
    
    def create_formation(self, formation: Formation) -> None:
        """Register a formation."""
        self.formations[formation.formation_id] = formation
    
    def start_kill_chain(self, target_id: str) -> KillChainTracker:
        """Initialize a kill chain tracker for a target."""
        tracker = KillChainTracker(target_id=target_id, phase="find")
        self.kill_chains[target_id] = tracker
        return tracker
    
    def update_kill_chain(self, target_id: str, phase: str) -> Optional[KillChainTracker]:
        """Update kill chain phase."""
        tracker = self.kill_chains.get(target_id)
        if tracker:
            tracker.advance_phase(phase)
        return tracker
    
    def get_units_by_domain(self, domain: DomainType, team: Optional[str] = None) -> List[Unit]:
        """Get all units in a domain, optionally filtered by team."""
        result = [u for u in self.units.values() if u.domain == domain]
        if team:
            result = [u for u in result if u.team == team]
        return result
    
    def get_units_by_state(self, state) -> List[Unit]:
        """Get all units in a given state."""
        return [u for u in self.units.values() if u.state.value == state.value]
    
    def get_contacts_in_range(self, position, range_meters: float, domain: DomainType = None) -> List[Contact]:
        """Get all contacts within a certain range."""
        result = []
        for contact in self.contacts.values():
            # Calculate distance
            dx = contact.position[0] - position[0]
            dy = contact.position[1] - position[1]
            dz = contact.position[2] - position[2]
            dist = (dx ** 2 + dy ** 2 + dz ** 2) ** 0.5
            
            if dist <= range_meters:
                if domain is None or contact.domain == domain:
                    result.append(contact)
        return result
    
    def advance_tick(self) -> None:
        """Advance the world state by one tick."""
        self.tick_count += 1
    
    def get_stats(self) -> dict:
        """Get world state statistics."""
        return {
            "tick_count": self.tick_count,
            "total_units": len(self.units),
            "total_contacts": len(self.contacts),
            "blue_forces": self.blue_force_count,
            "red_forces": self.red_force_count,
            "formations": len(self.formations),
            "active_kill_chains": len(self.kill_chains),
        }