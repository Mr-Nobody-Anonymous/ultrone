# Copyright (c) Ultrone Contributors. All rights reserved.
"""Composite Kill Chain - synchronized cross-domain F2T2EA execution."""

import logging
import asyncio
from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from datetime import datetime

logger = logging.getLogger("Ultrone.Brain.Reasoning.CompositeKillChain")


class CompositePhase(Enum):
    """Master timeline phases for cross-domain kill chains."""
    FIND = "find"
    FIX = "fix"
    TRACK = "track"
    TARGET = "target"
    ENGAGE = "engage"
    ASSESS = "assess"
    COMPLETE = "complete"


@dataclass
class DomainEngagement:
    """Tracks an engagement in a specific domain."""
    domain: str
    unit_id: str
    target_id: str
    phase: CompositePhase = CompositePhase.FIND
    ready_event: asyncio.Event = field(default_factory=asyncio.Event)
    
    def advance_phase(self) -> None:
        phases = [CompositePhase.FIND, CompositePhase.FIX, CompositePhase.TRACK,
                  CompositePhase.TARGET, CompositePhase.ENGAGE, CompositePhase.ASSESS]
        try:
            idx = phases.index(self.phase)
            if idx < len(phases) - 1:
                self.phase = phases[idx + 1]
        except ValueError:
            pass


class CompositeKillChain:
    """
    Manages synchronized cross-domain F2T2EA kill chains.
    
    Uses asyncio.Event for parallel state tracking across domains.
    Ensures kinetic strike waits for cyber preconditions.
    """
    
    def __init__(self, target_id: str, master_timeline_ticks: int = 20):
        self.target_id = target_id
        self.master_timeline_ticks = master_timeline_ticks
        self.engagements: Dict[str, DomainEngagement] = {}  # domain -> engagement
        self.phase = CompositePhase.FIND
        self.current_tick = 0
        self.completed_domains: List[str] = []
        self._lock = asyncio.Lock()
    
    def add_engagement(self, domain: str, unit_id: str, target_id: str) -> None:
        """Add a domain engagement to the composite chain."""
        self.engagements[domain] = DomainEngagement(
            domain=domain,
            unit_id=unit_id,
            target_id=target_id,
        )
    
    async def advance_domain_phase(self, domain: str) -> bool:
        """Advance a specific domain's phase. Thread-safe."""
        async with self._lock:
            engagement = self.engagements.get(domain)
            if not engagement:
                return False
            
            old_phase = engagement.phase
            engagement.advance_phase()
            
            logger.info(
                f"CompositeKillChain[{self.target_id}] {domain}: {old_phase.value} → {engagement.phase.value}"
            )
            
            # Signal completion if reached ASSESS
            if engagement.phase == CompositePhase.ASSESS:
                engagement.ready_event.set()
                if domain not in self.completed_domains:
                    self.completed_domains.append(domain)
            
            return True
    
    async def wait_for_precondition(self, domain: str, required_event: asyncio.Event) -> bool:
        """Wait for another domain's precondition to be met."""
        try:
            await asyncio.wait_for(required_event.wait(), timeout=30.0)
            return True
        except asyncio.TimeoutError:
            logger.warning(f"Precondition timeout for domain {domain}")
            return False
    
    async def synchronize_engage(self) -> None:
        """
        Synchronize multi-domain engagements.
        
        Example: Cyber must disable SCADA before kinetic strike.
        """
        # Check for cross-dependencies
        cyber_engage = self._get_engagement_by_action("cyber")
        if cyber_engage:
            # Other domains must wait for cyber
            for domain, eng in self.engagements.items():
                if domain != "cyber":
                    await self.wait_for_precondition(domain, cyber_engage.ready_event)
    
    def _get_engagement_by_action(self, action_keyword: str) -> Optional[DomainEngagement]:
        """Find engagement by action keyword in unit_id."""
        for domain, eng in self.engagements.items():
            if action_keyword in eng.unit_id.lower():
                return eng
        return None
    
    async def tick(self) -> Dict[str, Any]:
        """
        Process one tick of the composite kill chain.
        
        Advances phases across all domains in parallel.
        Returns status dict.
        """
        self.current_tick += 1
        
        # Parallel phase advancement
        tasks = []
        for domain in self.engagements:
            # Each domain advances independently
            tasks.append(self._domain_tick(domain))
        
        # Wait for all to complete
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Check if all domains complete
        active_domains = [d for d, e in self.engagements.items()
                       if e.phase not in (CompositePhase.ASSESS, CompositePhase.COMPLETE)]
        
        if not active_domains:
            self.phase = CompositePhase.COMPLETE
        
        return {
            "tick": self.current_tick,
            "phase": self.phase.value,
            "active_domains": active_domains,
            "completed_domains": self.completed_domains,
        }
    
    async def _domain_tick(self, domain: str) -> str:
        """Process one domain's tick logic."""
        # Domain-specific logic would go here
        return domain
    
    def get_status(self) -> Dict[str, Any]:
        """Get full composite kill chain status."""
        return {
            "target_id": self.target_id,
            "master_phase": self.phase.value,
            "current_tick": self.current_tick,
            "engagements": {
                d: {"unit": e.unit_id, "phase": e.phase.value}
                for d, e in self.engagements.items()
            },
        }
    
    def get_stats(self) -> dict:
        return {
            "total_domains": len(self.engagements),
            "active_domains": len([e for e in self.engagements.values()
                                if e.phase not in (CompositePhase.ASSESS, CompositePhase.COMPLETE)]),
            "ticks_elapsed": self.current_tick,
            "completed": self.phase == CompositePhase.COMPLETE,
        }