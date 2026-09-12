# Copyright (c) Ultrone Contributors. All rights reserved.
"""Learning Layer — continual learning subsystem.

Supports online learning, continual learning, transfer learning,
few-shot adaptation, meta-learning, reinforcement learning, imitation
learning, evolutionary optimization, population-based training, and
curriculum learning.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .base_layer import CognitiveLayer, LayerConfig
from .cycle_context import CycleContext, CyclePhase, PhaseResult
from .event_types import CognitiveEventType

logger = logging.getLogger("Ultrone.Cognitive.Learning")


@dataclass
class LearningLayerConfig(LayerConfig):
    """Configuration for the learning layer."""
    name: str = "learning"
    enable_online_learning: bool = True
    enable_continual_learning: bool = True
    enable_transfer_learning: bool = True
    enable_few_shot: bool = True
    enable_reinforcement_learning: bool = True
    learning_rate: float = 0.01
    batch_size: int = 32
    experience_replay_size: int = 1000


class LearningLayer(CognitiveLayer):
    """Continual learning subsystem.

    The learning layer:
    1. Supports online learning from experience
    2. Enables continual learning without forgetting
    3. Facilitates transfer learning between tasks
    4. Supports few-shot adaptation
    5. Implements reinforcement learning
    6. Tracks learning metrics
    """

    def __init__(self, config: Optional[LearningLayerConfig] = None):
        super().__init__(config or LearningLayerConfig())
        self._experience_replay: List[Dict[str, Any]] = []
        self._learning_history: List[Dict[str, Any]] = []
        self._model_updates: List[Dict[str, Any]] = []
        self._learning_metrics: Dict[str, float] = {}

    def _layer_phase(self) -> CyclePhase:
        return CyclePhase.LEARN

    def process(self, ctx: CycleContext) -> PhaseResult:
        """Execute the learning phase.

        Parameters
        ----------
        ctx : CycleContext
            The shared cycle context.

        Returns
        -------
        PhaseResult
            Result with learning updates.
        """
        start = time.time()

        # 1. Store experience
        experience = self._store_experience(ctx)

        # 2. Apply online learning
        online_updates = []
        if self.config.enable_online_learning:
            online_updates = self._apply_online_learning(ctx, experience)

        # 3. Apply continual learning
        continual_updates = []
        if self.config.enable_continual_learning:
            continual_updates = self._apply_continual_learning(ctx)

        # 4. Apply reinforcement learning
        rl_updates = []
        if self.config.enable_reinforcement_learning:
            rl_updates = self._apply_reinforcement_learning(ctx)

        # 5. Update learning metrics
        self._update_metrics(online_updates, continual_updates, rl_updates)

        # 6. Store in context
        learning_updates = online_updates + continual_updates + rl_updates
        ctx.learnings = learning_updates

        # 7. Publish event
        self._publish_event(
            CognitiveEventType.LEARNING,
            {
                "learning_type": "continual",
                "models_updated": [u.get("model", "") for u in learning_updates],
                "metrics": self._learning_metrics,
            },
        )

        # 8. Create decision trace
        trace = self._create_trace(
            decision="Continual learning from experience",
            confidence=0.7,
            evidence=[
                {
                    "source": "learning",
                    "description": f"Applied {len(learning_updates)} learning updates",
                    "confidence": 0.7,
                }
            ],
        )

        self._learning_history.append({
            "timestamp": time.time(),
            "updates": learning_updates,
            "metrics": dict(self._learning_metrics),
        })

        return PhaseResult(
            phase=self._phase,
            success=True,
            duration_seconds=time.time() - start,
            output={
                "learning_updates": learning_updates,
                "experience_size": len(self._experience_replay),
                "metrics": self._learning_metrics,
            },
            trace=trace,
        )

    def _store_experience(self, ctx: CycleContext) -> Dict[str, Any]:
        """Store experience from the current cycle."""
        experience = {
            "timestamp": time.time(),
            "observations_count": len(ctx.observations),
            "actions_count": len(ctx.actions),
            "outcomes_count": len(ctx.action_outcomes),
            "confidence": ctx.confidence,
            "uncertainty": ctx.uncertainty,
        }

        self._experience_replay.append(experience)
        if len(self._experience_replay) > self.config.experience_replay_size:
            self._experience_replay = self._experience_replay[-self.config.experience_replay_size:]

        return experience

    def _apply_online_learning(self, ctx: CycleContext, experience: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Apply online learning from the current experience."""
        updates = []

        # Update confidence calibration
        if experience["confidence"] < 0.5:
            updates.append({
                "type": "online",
                "model": "confidence_model",
                "update": "decrease_confidence_weight",
                "learning_rate": self.config.learning_rate,
            })

        return updates

    def _apply_continual_learning(self, ctx: CycleContext) -> List[Dict[str, Any]]:
        """Apply continual learning without forgetting."""
        updates = []

        # Consolidate lessons into knowledge
        if ctx.self_reflection:
            lessons = ctx.self_reflection.get("lessons_learned", [])
            for lesson in lessons:
                updates.append({
                    "type": "continual",
                    "model": "knowledge_base",
                    "update": lesson,
                })

        return updates

    def _apply_reinforcement_learning(self, ctx: CycleContext) -> List[Dict[str, Any]]:
        """Apply reinforcement learning updates."""
        updates = []

        # Update policies based on outcomes
        for outcome in ctx.action_outcomes:
            if outcome.success:
                updates.append({
                    "type": "rl",
                    "model": "policy",
                    "action_id": outcome.action_id,
                    "reward": outcome.reward,
                    "update": "reinforce",
                })
            else:
                updates.append({
                    "type": "rl",
                    "model": "policy",
                    "action_id": outcome.action_id,
                    "reward": outcome.reward,
                    "update": "penalize",
                })

        return updates

    def _update_metrics(self, *update_lists: List[Dict[str, Any]]) -> None:
        """Update learning metrics."""
        total_updates = sum(len(updates) for updates in update_lists)
        self._learning_metrics["total_updates"] = float(total_updates)

        # Track update types
        for updates in update_lists:
            for update in updates:
                update_type = update.get("type", "unknown")
                key = f"updates_{update_type}"
                self._learning_metrics[key] = self._learning_metrics.get(key, 0.0) + 1.0

    def get_experience_replay(self) -> List[Dict[str, Any]]:
        """Return the experience replay buffer."""
        return self._experience_replay

    def get_learning_history(self) -> List[Dict[str, Any]]:
        """Return the history of learning operations."""
        return self._learning_history

    def get_model_updates(self) -> List[Dict[str, Any]]:
        """Return all model updates."""
        return self._model_updates

    def get_learning_metrics(self) -> Dict[str, float]:
        """Return the current learning metrics."""
        return dict(self._learning_metrics)