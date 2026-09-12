# Copyright (c) Ultrone Contributors. All rights reserved.
"""F2T2EA Kill Chain state machine implementation."""

from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from datetime import datetime


class KillChainPhase(Enum):
    """The F2T2EA kill chain phases."""
    FIND = "find"       # Detect the target
    FIX = "fix"         # Stabilize the track
    TRACK = "track"     # Continuous tracking
    TARGET = "target"   # Prioritize and assign
    ENGAGE = "engage"   # Apply weapon
    ASSESS = "assess"   # Battle damage assessment


@dataclass
class PhaseState:
    """State for a single kill chain phase."""
    phase: KillChainPhase
    entered_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    completed: bool = False
    duration_ms: float = 0.0
    success: bool = False
    notes: str = ""


class KillChainStateMachine:
    """
    Strict F2T2EA state machine for target engagement.
    
    Progresses through phases in order, with timeout and
    success/failure tracking.
    """
    
    PHASE_TIMEOUT_MS = 60000  # 60 seconds per phase
    
    def __init__(self, target_id: str, max_duration_ms: float = 300000):
        self.target_id = target_id
        self.max_duration_ms = max_duration_ms
        self.current_phase = KillChainPhase.FIND
        self.phase_states: Dict[KillChainPhase, PhaseState] = {}
        self.started_at = datetime.utcnow().isoformat()
        self.completed = False
        self.successful = False
    
    def advance_phase(self, success: bool = True, notes: str = "") -> bool:
        """
        Advance to next phase. Returns True if advanced.
        
        Transitions: FIND -> FIX -> TRACK -> TARGET -> ENGAGE -> ASSESS
        """
        # Record current phase completion
        if self.current_phase in self.phase_states:
            state = self.phase_states[self.current_phase]
            state.completed = True
            state.success = success
            state.notes = notes
        
        # Move to next
        phases = [
            KillChainPhase.FIND, KillChainPhase.FIX, KillChainPhase.TRACK,
            KillChainPhase.TARGET, KillChainPhase.ENGAGE, KillChainPhase.ASSESS
        ]
        
        try:
            idx = phases.index(self.current_phase)
            if idx < len(phases) - 1:
                self.current_phase = phases[idx + 1]
                self.phase_states[self.current_phase] = PhaseState(
                    phase=self.current_phase
                )
                
                # If we reached ASSESS, we're done
                if self.current_phase == KillChainPhase.ASSESS:
                    self.completed = True
                    self.successful = success
                
                return True
        except ValueError:
            pass
        
        return False
    
    def get_progress(self) -> float:
        """Get progress through kill chain (0.0-1.0)."""
        phases = [KillChainPhase.FIND, KillChainPhase.FIX, KillChainPhase.TRACK,
                  KillChainPhase.TARGET, KillChainPhase.ENGAGE, KillChainPhase.ASSESS]
        try:
            return (phases.index(self.current_phase) + 1) / len(phases)
        except ValueError:
            return 0.0
    
    def get_elapsed_ms(self) -> float:
        """Get elapsed time in milliseconds."""
        try:
            start = datetime.fromisoformat(self.started_at)
            elapsed = (datetime.utcnow() - start).total_seconds() * 1000
            return elapsed
        except (ValueError, TypeError):
            return 0.0
    
    def is_timed_out(self) -> bool:
        """Check if kill chain has exceeded max duration."""
        return self.get_elapsed_ms() > self.max_duration_ms
    
    def get_summary(self) -> str:
        """Get human-readable kill chain status."""
        status = "COMPLETE" if self.completed else "ACTIVE"
        progress = self.get_progress()
        elapsed = self.get_elapsed_ms() / 1000
        
        return f"Kill Chain [{self.target_id}]: {status} | Phase: {self.current_phase.value} | Progress: {progress:.0%} | Elapsed: {elapsed:.1f}s"


class KillChain:
    """
    Manages multiple kill chains for different targets.
    
    Provides registry and coordination for concurrent engagements.
    """
    
    def __init__(self):
        self.chains: Dict[str, KillChainStateMachine] = {}
    
    def start(self, target_id: str, max_duration_ms: float = 300000) -> KillChainStateMachine:
        """Start a new kill chain for a target."""
        chain = KillChainStateMachine(target_id, max_duration_ms)
        self.chains[target_id] = chain
        return chain
    
    def get(self, target_id: str) -> Optional[KillChainStateMachine]:
        """Get a kill chain by target ID."""
        return self.chains.get(target_id)
    
    def advance(self, target_id: str, success: bool = True, notes: str = "") -> bool:
        """Advance a kill chain phase."""
        chain = self.chains.get(target_id)
        if chain:
            return chain.advance_phase(success, notes)
        return False
    
    def complete(self, target_id: str, success: bool = True) -> bool:
        """Mark a kill chain as complete."""
        chain = self.chains.get(target_id)
        if chain:
            chain.completed = True
            chain.successful = success
            return True
        return False
    
    def remove(self, target_id: str) -> Optional[KillChainStateMachine]:
        """Remove a completed kill chain."""
        return self.chains.pop(target_id, None)
    
    def get_active(self) -> List[KillChainStateMachine]:
        """Get all active kill chains."""
        return [c for c in self.chains.values() if not c.completed]
    
    def get_stats(self) -> dict:
        return {
            "total_chains": len(self.chains),
            "active_chains": len(self.get_active()),
            "completed_chains": len(self.chains) - len(self.get_active()),
        }