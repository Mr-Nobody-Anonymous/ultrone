# Copyright (c) Ultrone Contributors. All rights reserved.
"""Simulation framework core: time, events, scheduling, telemetry,
evaluation, checkpointing, and batch experimentation.

Everything here is deterministic: identical (scenario, seed) produces
identical runs. Nothing in this package touches anything outside the
sandbox -- the SIMULATION SAFETY BOUNDARY established in
``sandbox/ucl.py`` applies unchanged.
"""

from __future__ import annotations

import hashlib
import json
import statistics
from collections import deque
from dataclasses import dataclass, field
from typing import Any, Callable, Deque, Dict, List, Optional, Tuple


# --------------------------------------------------------------------- #
# Clock                                                                  #
# --------------------------------------------------------------------- #
class SimulationClock:
    """Central deterministic discrete-time clock."""

    def __init__(self, start: int = 0, dt_seconds: float = 1.0) -> None:
        self._tick = int(start)
        self.dt_seconds = float(dt_seconds)

    @property
    def tick(self) -> int:
        return self._tick

    def advance(self, n: int = 1) -> int:
        self._tick += max(1, int(n))
        return self._tick

    def reset(self, tick: int = 0) -> None:
        self._tick = int(tick)


# --------------------------------------------------------------------- #
# Events                                                                 #
# --------------------------------------------------------------------- #
@dataclass
class ScheduledEvent:
    tick: int
    name: str
    action: Callable[[Any], None]     # receives the running scenario
    fired: bool = False


class EventBus:
    """Time-based events, fired in deterministic (tick, name) order."""

    def __init__(self) -> None:
        self._events: List[ScheduledEvent] = []
        self.fired_log: List[Tuple[int, str]] = []

    def schedule(self, tick: int, name: str,
                 action: Callable[[Any], None]) -> None:
        self._events.append(ScheduledEvent(int(tick), name, action))

    def fire_due(self, tick: int, scenario: Any) -> List[str]:
        due = sorted(
            (e for e in self._events if not e.fired and e.tick <= tick),
            key=lambda e: (e.tick, e.name),
        )
        fired: List[str] = []
        for e in due:
            e.action(scenario)
            e.fired = True
            self.fired_log.append((e.tick, e.name))
            fired.append(e.name)
        self._events = [e for e in self._events if not e.fired]
        return fired


# --------------------------------------------------------------------- #
# Task scheduler                                                         #
# --------------------------------------------------------------------- #
@dataclass
class ScheduledTask:
    platform_id: str
    task: Dict[str, Any]
    start_tick: int = 0
    priority: int = 1


class Scheduler:
    """Dispatches queued tasks to platforms when they come due."""

    def __init__(self) -> None:
        self.queue: List[ScheduledTask] = []

    def enqueue(self, task: ScheduledTask) -> None:
        self.queue.append(task)

    def pop_due(self, tick: int) -> List[ScheduledTask]:
        due = [t for t in self.queue if t.start_tick <= tick]
        ordered = sorted(due, key=lambda t: (-t.priority, t.start_tick))
        for t in ordered:
            self.queue.remove(t)
        return ordered

    @property
    def pending(self) -> int:
        return len(self.queue)


# --------------------------------------------------------------------- #
# Telemetry                                                              #
# --------------------------------------------------------------------- #
class TelemetryRecorder:
    """Per-tick state frames, exportable as JSON."""

    def __init__(self) -> None:
        self.frames: List[Dict[str, Any]] = []

    def record(self, tick: int, states: Dict[str, Any],
               extra: Optional[Dict[str, Any]] = None) -> None:
        frame: Dict[str, Any] = {"tick": tick, "states": states}
        if extra:
            frame.update(extra)
        self.frames.append(frame)

    def export(self) -> List[Dict[str, Any]]:
        return [json.loads(json.dumps(f, sort_keys=True, default=str))
                for f in self.frames]

    def fingerprint(self) -> str:
        payload = json.dumps(self.export(), sort_keys=True,
                             separators=(",", ":"))
        return hashlib.sha256(payload.encode()).hexdigest()[:16]


# --------------------------------------------------------------------- #
# Evaluation                                                             #
# --------------------------------------------------------------------- #
class Evaluator:
    """Mission-performance measurement over completed task results."""

    @staticmethod
    def evaluate(results: List[Dict[str, Any]],
                 hard_violations: int = 0,
                 energy_used: float = 0.0) -> Dict[str, Any]:
        total = len(results) or 1
        succeeded = sum(1 for r in results if r.get("success"))
        return {
            "tasks_total": len(results),
            "tasks_succeeded": succeeded,
            "task_completion_rate": round(succeeded / total, 4),
            "hard_violations": hard_violations,
            "energy_used_proxy": round(energy_used, 3),
            "safe_completion": bool(
                succeeded == len(results) and hard_violations == 0),
        }


# --------------------------------------------------------------------- #
# Checkpoints                                                            #
# --------------------------------------------------------------------- #
class CheckpointManager:
    """Snapshot / restore / clone of a running scenario.

    Machine state is captured from each machine's ``__dict__``, keeping
    only JSON-safe values (RNG handles and callbacks are excluded). A
    restored scenario continues from an exact recorded state; a clone is
    a fresh lab restored to that same state.
    """

    @staticmethod
    def _capture_obj(obj: Any) -> Dict[str, Any]:
        safe: Dict[str, Any] = {}
        for key, value in vars(obj).items():
            try:
                json.dumps(value, sort_keys=True)
                safe[key] = value
            except (TypeError, ValueError):
                continue                     # rng/callbacks/etc. skipped
        return safe

    @staticmethod
    def snapshot(scenario) -> Dict[str, Any]:
        return {
            "name": scenario.spec.name,
            "seed": scenario.spec.seed,
            "tick": scenario.clock.tick,
            "machines": {
                mid: CheckpointManager._capture_obj(m)
                for mid, m in scenario.lab.machine_controller.machines.items()
            },
            "world": {
                "tick": scenario.lab.world.environment["tick"],
                "n_comms": len(scenario.lab.world.communications),
            },
        }

    @staticmethod
    def restore(scenario, state: Dict[str, Any]) -> None:
        scenario.clock.reset(state["tick"])
        scenario.lab.world.environment["tick"] = state["world"]["tick"]
        for mid, saved in state["machines"].items():
            machine = scenario.lab.machine_controller.machines[mid]
            for key, value in saved.items():
                setattr(machine, key, value)

    @staticmethod
    def clone(scenario, state: Dict[str, Any]):
        fresh = type(scenario)(scenario.spec)
        CheckpointManager.restore(fresh, state)
        return fresh


# --------------------------------------------------------------------- #
# Experiment runner                                                      #
# --------------------------------------------------------------------- #
class ExperimentRunner:
    """Run the same scenario across many seeds; aggregate outcomes."""

    @staticmethod
    def run_batch(scenario_factory: Callable[[int], Any],
                  seeds: List[int]) -> Dict[str, Any]:
        evaluations: List[Dict[str, Any]] = []
        for seed in seeds:
            scenario = scenario_factory(seed)
            report = scenario.run()
            evaluations.append(report["evaluation"])
        rates = [e["task_completion_rate"] for e in evaluations]
        violations = sum(e["hard_violations"] for e in evaluations)
        safe_runs = sum(1 for e in evaluations if e["safe_completion"])
        mean_rate = statistics.mean(rates) if rates else 0.0
        stdev = statistics.pstdev(rates) if len(rates) > 1 else 0.0
        return {
            "seeds": list(seeds),
            "runs": len(seeds),
            "mean_task_completion_rate": round(mean_rate, 4),
            "completion_stdev": round(stdev, 4),
            "total_hard_violations": violations,
            "safe_runs": safe_runs,
            "all_runs_safe": safe_runs == len(seeds),
            "evaluations": evaluations,
        }