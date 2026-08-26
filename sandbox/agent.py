# Copyright (c) Ultrone Contributors. All rights reserved.
"""GeneralAgent: the integration layer tying every capability together.

Perception-free minimal loop matching the Sprint D architecture:

    memory + goals + tools + world model + self-critique

inside one agent whose ONLY effect is sandbox outcomes recorded in its own
memory and (optionally) an audit store. This is where "capabilities"
become "a system": tasks flow through goal management, tool composition,
world-model prediction, experience updates, and post-hoc self-review.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from sandbox.critique import SelfCritic
from sandbox.memory import EpisodicMemory, GoalStack
from sandbox.prediction import PredictionRecord
from sandbox.tooluse import build_demo_toolbox
from sandbox.world_model import TransitionModel


@dataclass
class EpisodeResult:
    task_id: str
    success: bool
    detail: Dict[str, Any] = field(default_factory=dict)


class GeneralAgent:
    def __init__(self, seed: int = 0) -> None:
        self.rng = random.Random(seed)
        self.memory = EpisodicMemory()
        self.goals = GoalStack()
        self.toolbox = build_demo_toolbox()
        self.world_model = TransitionModel()
        self.critic = SelfCritic()
        self.episodes = 0

    # -- task types --------------------------------------------------------- #
    def handle_tool_task(self, task_id: str, text: str,
                         needed_type: str = "count") -> EpisodeResult:
        self.goals.push(task_id, f"compute {needed_type} of text")
        path = self.toolbox.chain("text", needed_type)
        if path is None:
            return EpisodeResult(task_id, False, {"reason": "no tool chain"})
        value = self.toolbox.execute(text, path)
        self.memory.remember(
            task_id, f"tool chain answered {value}",
            tags=("tool", task_id), tick=self.episodes,
        )
        self.goals.complete(task_id)
        self.episodes += 1
        return EpisodeResult(task_id, True, {
            "value": value, "chain": [t.name for t in path],
        })

    def handle_world_task(self, task_id: str, state: str, action: str,
                          observed_next: str) -> EpisodeResult:
        """Predict, then learn from the observed outcome (in-sim only)."""
        self.goals.push(task_id, f"predict {state}--{action}-->?")
        predicted = self.world_model.predict(state, action)
        surprise = self.world_model.surprise(state, action, observed_next)
        self.world_model.update(state, action, observed_next)
        self.memory.remember(
            task_id,
            f"{state}-{action}->{observed_next} surprise={surprise}",
            tags=("world", state), tick=self.episodes,
        )
        self.goals.complete(task_id)
        self.episodes += 1
        return EpisodeResult(task_id, True, {
            "surprise": surprise,
            "had_prior": bool(predicted),
            "predicted_next": predicted,
        })

    def predict_transition(self, state: str, action: str) -> Optional[str]:
        dist = self.world_model.predict(state, action)
        if not dist:
            return None
        return sorted(dist.items(), key=lambda kv: (-kv[1], kv[0]))[0][0]

    # -- self-review ---------------------------------------------------------- #
    def review_prediction_history(self, records: List[PredictionRecord]) -> int:
        critiques = self.critic.review_predictions(records, subject_id="general-agent")
        for i, c in enumerate(critiques):
            self.memory.remember(
                f"critique-{self.episodes}-{i}", f"{c.kind}: {c.detail}",
                tags=("critique", c.kind), salience=c.severity,
                tick=self.episodes,
            )
        return len(critiques)

    # -- introspection ---------------------------------------------------------- #
    @property
    def completed_goals(self) -> int:
        return sum(
            1 for g in self.goals.goals.values() if g.status == "DONE"
        )

    def recall_about(self, keyword: str, k: int = 3) -> List[str]:
        return [m.content for m in self.memory.recall(keywords=(keyword,), k=k)]

    # -- machine control ------------------------------------------------- #
    def attach_machines(self, controller) -> None:
        """Attach a sandbox MachineController (simulation-only)."""
        self.machines = controller

    def handle_machine_task(
        self, task_id: str, machine_id: str,
        read, actuate, target: float, tolerance: float,
        tick_limit: int = 100, gain: float = 0.3,
    ) -> EpisodeResult:
        """Closed-loop setpoint task on one attached machine.

        Uses the proportional policy; every out-of-envelope command is
        refused by the machine's interlock and recorded. Success requires
        settling within tolerance AND zero new hard violations.
        """
        from sandbox.machines import run_setpoint_task

        self.goals.push(task_id, f"drive {machine_id} to {target}")
        violations_before = self.machines.hard_violations
        result = run_setpoint_task(
            self.machines, machine_id, tick_limit=tick_limit,
            read=read, actuate=actuate, target=target,
            tolerance=tolerance, gain=gain,
        )
        clean = (self.machines.hard_violations == violations_before)
        success = bool(result["settled"] and clean)
        if success:
            self.goals.complete(task_id)
        self.memory.remember(
            task_id,
            f"machine {machine_id} target={target} settled={result['settled']} "
            f"clean={clean}",
            tags=("machine", machine_id), tick=self.episodes,
        )
        self.episodes += 1
        return EpisodeResult(task_id, success, {**result, "clean": clean})
