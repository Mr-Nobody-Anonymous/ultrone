# Copyright (c) Ultrone Contributors. All rights reserved.
"""Team reasoning and shared belief models for multi-agent coordination.

Implements shared mental models, team situation awareness, and
collective intention formation for cohesive multi-agent teams.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set

from .base import BaseCoordinator, CoordinationConfig

logger = logging.getLogger("Ultrone.Brain.Reasoning.Coordination.TeamReasoning")


@dataclass
class TeamReasoningConfig(CoordinationConfig):
    """Configuration for team reasoning."""
    belief_alignment_threshold: float = 0.7
    max_belief_exchange_rounds: int = 5
    shared_goal_formation: bool = True


@dataclass
class Belief:
    """A single belief held by an agent about the world state."""
    concept: str
    value: Any
    confidence: float = 1.0
    source: str = ""
    timestamp: float = field(default_factory=time.time)


class TeamReasoning(BaseCoordinator):
    """Team reasoning with shared belief models.

    Enables agents to form shared mental models by aligning their
    individual beliefs through communication. Supports:
    - Belief alignment via consensus rounds
    - Shared goal formation
    - Team situation awareness
    - Collective intention recognition
    """

    def __init__(self, config: Optional[TeamReasoningConfig] = None):
        super().__init__(config or TeamReasoningConfig())
        self._config: TeamReasoningConfig = self.config  # type: ignore
        self._agent_beliefs: Dict[str, Dict[str, Belief]] = {}
        self._shared_beliefs: Dict[str, Belief] = {}
        self._team_goals: List[Dict[str, Any]] = []

    def register_agent(self, agent_id: str) -> None:
        """Register an agent for team reasoning."""
        if agent_id not in self._agent_beliefs:
            self._agent_beliefs[agent_id] = {}
            logger.debug("Agent %s registered for team reasoning", agent_id)

    def update_belief(self, agent_id: str, concept: str, value: Any, confidence: float = 1.0) -> None:
        """Update an agent's belief about a concept."""
        if agent_id not in self._agent_beliefs:
            self.register_agent(agent_id)
        self._agent_beliefs[agent_id][concept] = Belief(
            concept=concept, value=value, confidence=confidence, source=agent_id,
        )

    def align_beliefs(self, concept: str) -> Optional[Belief]:
        """Align beliefs about a concept across all agents.

        Uses weighted voting based on confidence scores.
        Returns the aligned belief, or None if alignment threshold not met.
        """
        beliefs = []
        for agent_id, agent_beliefs in self._agent_beliefs.items():
            if concept in agent_beliefs:
                beliefs.append(agent_beliefs[concept])

        if not beliefs:
            return None

        # Compute weighted alignment score
        total_confidence = sum(b.confidence for b in beliefs)
        if total_confidence == 0:
            return None

        # Find most common value weighted by confidence
        value_scores: Dict[Any, float] = {}
        for b in beliefs:
            key = str(b.value) if not isinstance(b.value, (int, float, str, bool)) else b.value
            value_scores[key] = value_scores.get(key, 0.0) + b.confidence

        best_value = max(value_scores, key=value_scores.get)
        alignment_score = value_scores[best_value] / total_confidence

        if alignment_score >= self._config.belief_alignment_threshold:
            aligned = Belief(
                concept=concept,
                value=best_value,
                confidence=alignment_score,
                source="team",
            )
            self._shared_beliefs[concept] = aligned
            logger.info("Belief aligned on '%s' = %s (confidence=%.2f)", concept, best_value, alignment_score)
            return aligned

        logger.debug("Belief alignment failed for '%s' (score=%.2f)", concept, alignment_score)
        return None

    def form_shared_goals(self, context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Form shared team goals from aligned beliefs."""
        if not self._config.shared_goal_formation:
            return []

        goals = []
        # Example: If enemy detected with high confidence, form engage goal
        enemy_belief = self._shared_beliefs.get("enemy_position")
        threat_belief = self._shared_beliefs.get("threat_level")

        if enemy_belief and enemy_belief.confidence > 0.7:
            goals.append({
                "goal": "neutralize_threat",
                "target": enemy_belief.value,
                "priority": (threat_belief.value if threat_belief else 0.5),
                "formation": "team",
            })

        if threat_belief and threat_belief.value == "high":
            goals.append({
                "goal": "activate_countermeasures",
                "priority": 0.9,
            })

        self._team_goals = goals
        return goals

    def coordinate(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Coordinate team reasoning in a single step.

        Context keys:
        - agent_beliefs: Dict[agent_id, Dict[concept, (value, confidence)]]
        - align_on: List of concepts to align
        """
        agent_beliefs = context.get("agent_beliefs", {})
        align_on = context.get("align_on", [])

        for agent_id, beliefs in agent_beliefs.items():
            for concept, (value, confidence) in beliefs.items():
                self.update_belief(agent_id, concept, value, confidence)

        # Align specified beliefs
        for concept in align_on:
            self.align_beliefs(concept)

        # Form shared goals
        goals = self.form_shared_goals(context)

        return {
            "shared_beliefs": {k: {"value": v.value, "confidence": v.confidence}
                               for k, v in self._shared_beliefs.items()},
            "team_goals": goals,
            "aligned_concepts": len(align_on),
        }

    def get_stats(self) -> Dict[str, Any]:
        return {
            "type": "TeamReasoning",
            "agents": len(self._agent_beliefs),
            "shared_beliefs": len(self._shared_beliefs),
            "team_goals": len(self._team_goals),
            "alignment_threshold": self._config.belief_alignment_threshold,
        }

