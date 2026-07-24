# Copyright (c) Ultrone Contributors. All rights reserved.
"""Emergent behavior analysis for multi-agent systems.

Analyzes agent trajectories and interactions to detect emergent
patterns, phase transitions, and collective behaviors that arise
from local agent interactions.
"""

from __future__ import annotations

import logging
import numpy as np
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple

from .base import BaseCoordinator, CoordinationConfig

logger = logging.getLogger("Ultrone.Brain.Reasoning.Coordination.EmergentBehavior")


@dataclass
class EmergentBehaviorConfig(CoordinationConfig):
    """Configuration for emergent behavior analysis."""
    observation_window: int = 50
    clustering_eps: float = 0.3
    min_pattern_frequency: int = 3
    detect_phase_transitions: bool = True


@dataclass
class BehaviorPattern:
    """A detected pattern in agent behavior."""
    pattern_id: str
    pattern_type: str  # "swarming", "flocking", "dispersing", "herding", "flanking", "other"
    agents_involved: List[str]
    confidence: float
    description: str
    metrics: Dict[str, float] = field(default_factory=dict)


@dataclass
class PhaseTransition:
    """A detected phase transition in collective behavior."""
    transition_type: str  # "dispersed_to_clustered", "ordered_to_chaotic", etc.
    trigger_step: int
    order_parameter_before: float
    order_parameter_after: float
    significance: float


class EmergentBehavior(BaseCoordinator):
    """Analyzes emergent behaviors in multi-agent systems.

    Detects patterns such as:
    - Swarming: coordinated collective movement
    - Flocking: alignment of velocity vectors
    - Dispersing: agents spreading out
    - Flanking: surround/encirclement maneuvers
    - Phase transitions: sudden changes in collective state

    Uses order parameters from statistical physics (e.g., polarization,
    average nearest-neighbor distance) to quantify collective states.
    """

    def __init__(self, config: Optional[EmergentBehaviorConfig] = None):
        super().__init__(config or EmergentBehaviorConfig())
        self._config: EmergentBehaviorConfig = self.config  # type: ignore
        self._agent_trajectories: Dict[str, List[Tuple[float, float]]] = {}
        self._agent_velocities: Dict[str, List[Tuple[float, float]]] = {}
        self._detected_patterns: List[BehaviorPattern] = []
        self._phase_transitions: List[PhaseTransition] = []
        self._step_count: int = 0
        self._order_parameter_history: List[float] = []

    def record_step(
        self,
        positions: Dict[str, Tuple[float, float]],
        velocities: Optional[Dict[str, Tuple[float, float]]] = None,
    ) -> None:
        """Record agent positions and velocities for one simulation step."""
        self._step_count += 1
        for agent_id, pos in positions.items():
            self._agent_trajectories.setdefault(agent_id, []).append(pos)
            # Keep window size bounded
            if len(self._agent_trajectories[agent_id]) > self._config.observation_window:
                self._agent_trajectories[agent_id].pop(0)

        if velocities:
            for agent_id, vel in velocities.items():
                self._agent_velocities.setdefault(agent_id, []).append(vel)
                if len(self._agent_velocities[agent_id]) > self._config.observation_window:
                    self._agent_velocities[agent_id].pop(0)

        # Compute order parameters and detect patterns
        if self._step_count % 5 == 0:
            self._detect_patterns()
            if self._config.detect_phase_transitions:
                self._detect_phase_transitions()

    def _compute_polarization(self) -> float:
        """Compute the polarization order parameter.

        Polarization = |sum(velocity_unit_vectors)| / N
        Ranges from 0 (disordered) to 1 (perfectly aligned).
        """
        if not self._agent_velocities:
            return 0.0
        recent_vels = []
        for agent_id, vels in self._agent_velocities.items():
            if vels:
                v = vels[-1]
                speed = np.sqrt(v[0] ** 2 + v[1] ** 2)
                if speed > 0:
                    recent_vels.append((v[0] / speed, v[1] / speed))
        if not recent_vels:
            return 0.0
        sum_x = sum(v[0] for v in recent_vels)
        sum_y = sum(v[1] for v in recent_vels)
        return np.sqrt(sum_x ** 2 + sum_y ** 2) / len(recent_vels)

    def _compute_mean_distance(self) -> float:
        """Compute mean nearest-neighbor distance between agents."""
        positions = {}
        for agent_id, traj in self._agent_trajectories.items():
            if traj:
                positions[agent_id] = traj[-1]
        agents = list(positions.values())
        if len(agents) < 2:
            return 1.0
        total_dist = 0.0
        count = 0
        for i in range(len(agents)):
            min_dist = float("inf")
            for j in range(len(agents)):
                if i != j:
                    dist = np.sqrt((agents[i][0] - agents[j][0]) ** 2 + (agents[i][1] - agents[j][1]) ** 2)
                    min_dist = min(min_dist, dist)
            total_dist += min_dist
            count += 1
        return total_dist / count if count > 0 else 1.0

    def _detect_patterns(self) -> None:
        """Detect emergent behavior patterns from recent trajectories."""
        if len(self._agent_trajectories) < 2:
            return

        polarization = self._compute_polarization()
        mean_dist = self._compute_mean_distance()

        patterns = []

        # Flocking: high polarization and low mean distance
        if polarization > 0.7 and mean_dist < 0.3:
            agents = list(self._agent_trajectories.keys())
            patterns.append(BehaviorPattern(
                pattern_id=f"flock_{self._step_count}",
                pattern_type="flocking",
                agents_involved=agents,
                confidence=min(1.0, polarization * 1.2),
                description=f"Flocking behavior detected: polarization={polarization:.2f}",
                metrics={"polarization": polarization, "mean_distance": mean_dist},
            ))

        # Swarming: moderate polarization, agents in proximity
        if 0.3 < polarization < 0.7 and mean_dist < 0.5:
            agents = list(self._agent_trajectories.keys())
            patterns.append(BehaviorPattern(
                pattern_id=f"swarm_{self._step_count}",
                pattern_type="swarming",
                agents_involved=agents,
                confidence=0.6,
                description=f"Swarming behavior detected",
                metrics={"polarization": polarization, "mean_distance": mean_dist},
            ))

        # Dispersing: low polarization and increasing mean distance
        if polarization < 0.3 and mean_dist > 0.5:
            agents = list(self._agent_trajectories.keys())
            patterns.append(BehaviorPattern(
                pattern_id=f"disperse_{self._step_count}",
                pattern_type="dispersing",
                agents_involved=agents,
                confidence=0.7,
                description="Dispersing behavior detected",
                metrics={"polarization": polarization, "mean_distance": mean_dist},
            ))

        for pattern in patterns:
            if pattern.confidence > 0.5:
                self._detected_patterns.append(pattern)
                logger.info("Emergent pattern: %s (conf=%.2f)", pattern.pattern_type, pattern.confidence)

    def _detect_phase_transitions(self) -> None:
        """Detect phase transitions in collective behavior."""
        polarization = self._compute_polarization()
        self._order_parameter_history.append(polarization)

        if len(self._order_parameter_history) < 10:
            return

        # Detect rapid changes in order parameter
        window = min(10, len(self._order_parameter_history))
        recent = self._order_parameter_history[-window:]
        prev = self._order_parameter_history[-window * 2:-window] if len(self._order_parameter_history) >= window * 2 else recent

        if len(prev) >= 5 and len(recent) >= 5:
            mean_prev = np.mean(prev[-5:])
            mean_recent = np.mean(recent[-5:])
            change = abs(mean_recent - mean_prev)

            if change > 0.3:  # Significant change threshold
                transition_type = "ordered_to_chaotic" if mean_recent < mean_prev else "chaotic_to_ordered"
                self._phase_transitions.append(PhaseTransition(
                    transition_type=transition_type,
                    trigger_step=self._step_count,
                    order_parameter_before=mean_prev,
                    order_parameter_after=mean_recent,
                    significance=change,
                ))
                logger.info("Phase transition: %s (Δ=%.2f)", transition_type, change)

    def coordinate(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze emergent behavior.

        Context keys:
        - positions: Dict[agent_id, (x, y)]
        - velocities: Optional[Dict[agent_id, (vx, vy)]]
        """
        positions = context.get("positions", {})
        velocities = context.get("velocities")
        self.record_step(positions, velocities)

        return {
            "num_patterns_detected": len(self._detected_patterns),
            "recent_patterns": [p.pattern_type for p in self._detected_patterns[-5:]],
            "polarization": self._compute_polarization(),
            "mean_distance": self._compute_mean_distance(),
            "phase_transitions": [pt.transition_type for pt in self._phase_transitions[-3:]],
        }

    def get_stats(self) -> Dict[str, Any]:
        return {
            "type": "EmergentBehavior",
            "agents_tracked": len(self._agent_trajectories),
            "patterns_detected": len(self._detected_patterns),
            "phase_transitions": len(self._phase_transitions),
            "current_polarization": self._compute_polarization(),
            "current_mean_distance": self._compute_mean_distance(),
        }

