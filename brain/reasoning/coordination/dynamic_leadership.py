# Copyright (c) Ultrone Contributors. All rights reserved.
"""Dynamic leadership election for multi-agent systems.

Implements leadership election protocols where agents dynamically
select leaders based on capability, position, mission context, and
past performance. Supports role handover and distributed consensus.
"""

from __future__ import annotations

import logging
import numpy as np
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple

from .base import BaseCoordinator, CoordinationConfig

logger = logging.getLogger("Ultrone.Brain.Reasoning.Coordination.DynamicLeadership")


@dataclass
class LeadershipConfig(CoordinationConfig):
    """Configuration for dynamic leadership."""
    election_interval: int = 10
    leadership_score_fn: Optional[str] = None  # "capability", "position", "consensus"
    max_leader_history: int = 100
    min_confidence_to_lead: float = 0.5


@dataclass
class LeaderCandidate:
    """A candidate for leadership with scoring."""
    agent_id: str
    capability_score: float = 0.0
    position_score: float = 0.0
    experience_score: float = 0.0
    consensus_score: float = 0.0
    total_score: float = 0.0
    tenure: int = 0


class DynamicLeadership(BaseCoordinator):
    """Dynamic leadership election protocol.

    Agents elect leaders based on a configurable scoring function.
    Supports:
    - Capability-based leadership (most skilled agent leads)
    - Position-based leadership (centrally located agent leads)
    - Consensus-based leadership (agents vote)
    - Graceful leader handover on failure
    - Leader history for accountability
    """

    def __init__(self, config: Optional[LeadershipConfig] = None):
        super().__init__(config or LeadershipConfig())
        self._config: LeadershipConfig = self.config  # type: ignore
        self._current_leader: Optional[str] = None
        self._leader_history: List[Tuple[str, int]] = []
        self._candidates: Dict[str, LeaderCandidate] = {}
        self._step_count: int = 0
        self._agent_capabilities: Dict[str, float] = {}
        self._agent_positions: Dict[str, Tuple[float, float]] = {}

    def register_agent(self, agent_id: str, capabilities: Optional[Dict[str, float]] = None) -> None:
        """Register an agent for leadership consideration."""
        if agent_id not in self._candidates:
            self._candidates[agent_id] = LeaderCandidate(agent_id=agent_id)
            self._agent_capabilities[agent_id] = capabilities.get("overall", 0.5) if capabilities else 0.5
            logger.debug("Agent %s registered for leadership", agent_id)

    def update_position(self, agent_id: str, position: Tuple[float, float]) -> None:
        """Update agent position for position-based scoring."""
        self._agent_positions[agent_id] = position

    def update_capability(self, agent_id: str, capability: float) -> None:
        """Update agent capability score."""
        self._agent_capabilities[agent_id] = capability

    def elect_leader(self, force: bool = False) -> Optional[str]:
        """Run leadership election.

        Parameters
        ----------
        force:
            If True, force re-election regardless of interval.

        Returns
        -------
        Optional[str]
            The elected leader's agent ID.
        """
        self._step_count += 1
        if not force and self._step_count % self._config.election_interval != 0:
            return self._current_leader

        if not self._candidates:
            logger.warning("No candidates for leadership election.")
            return None

        # Score all candidates
        for agent_id, candidate in self._candidates.items():
            cap_score = self._agent_capabilities.get(agent_id, 0.5)

            # Position score (closer to centroid = higher)
            pos_score = 0.5
            if self._agent_positions:
                positions = list(self._agent_positions.values())
                centroid = (
                    np.mean([p[0] for p in positions]),
                    np.mean([p[1] for p in positions]),
                )
                if agent_id in self._agent_positions:
                    dist = np.sqrt(
                        (self._agent_positions[agent_id][0] - centroid[0]) ** 2 +
                        (self._agent_positions[agent_id][1] - centroid[1]) ** 2
                    )
                    pos_score = 1.0 / (1.0 + dist)

            # Experience score (agents who have led before get bonus)
            exp_score = min(1.0, candidate.tenure / 100.0)

            # Consensus score based on capability voting
            consensus_score = np.mean(list(self._agent_capabilities.values())) if self._agent_capabilities else 0.5

            # Total score (configurable weighting)
            if self._config.leadership_score_fn == "capability":
                total = cap_score
            elif self._config.leadership_score_fn == "position":
                total = pos_score
            elif self._config.leadership_score_fn == "consensus":
                total = consensus_score
            else:
                total = 0.4 * cap_score + 0.3 * pos_score + 0.2 * exp_score + 0.1 * consensus_score

            candidate.capability_score = cap_score
            candidate.position_score = pos_score
            candidate.experience_score = exp_score
            candidate.consensus_score = consensus_score
            candidate.total_score = total

        # Select leader with highest total score above threshold
        best = max(self._candidates.values(), key=lambda c: c.total_score)
        if best.total_score >= self._config.min_confidence_to_lead:
            if self._current_leader != best.agent_id:
                # Handover
                if self._current_leader:
                    self._leader_history.append((self._current_leader, self._step_count))
                    if len(self._leader_history) > self._config.max_leader_history:
                        self._leader_history.pop(0)
                self._current_leader = best.agent_id
                best.tenure += 1
                logger.info("Leadership elected: %s (score=%.3f)", best.agent_id, best.total_score)
            return self._current_leader

        logger.debug("No leader elected — best candidate below threshold (%.3f)", best.total_score)
        return self._current_leader

    def get_leader(self) -> Optional[str]:
        """Return the current leader's agent ID."""
        return self._current_leader

    def handover(self, reason: str = "manual") -> Optional[str]:
        """Force leadership handover to next best candidate."""
        if self._current_leader:
            agent_id = self._current_leader
            self._leader_history.append((agent_id, self._step_count))
            logger.info("Leadership handover from %s (reason: %s)", agent_id, reason)
        self._current_leader = None
        return self.elect_leader(force=True)

    def coordinate(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Run leadership coordination.

        Context keys:
        - agent_capabilities: Dict[agent_id, float]
        - agent_positions: Dict[agent_id, (x, y)]
        - force_election: bool
        """
        for agent_id, cap in context.get("agent_capabilities", {}).items():
            self.register_agent(agent_id)
            self.update_capability(agent_id, cap)

        for agent_id, pos in context.get("agent_positions", {}).items():
            self.update_position(agent_id, pos)

        leader = self.elect_leader(force=context.get("force_election", False))

        return {
            "leader": leader,
            "election_step": self._step_count,
            "candidates": {aid: {
                "total_score": c.total_score,
                "capability": c.capability_score,
                "position": c.position_score,
                "experience": c.experience_score,
            } for aid, c in self._candidates.items()},
            "history_length": len(self._leader_history),
        }

    def get_stats(self) -> Dict[str, Any]:
        return {
            "type": "DynamicLeadership",
            "current_leader": self._current_leader,
            "num_candidates": len(self._candidates),
            "elections_held": self._step_count // self._config.election_interval,
            "history_length": len(self._leader_history),
        }

