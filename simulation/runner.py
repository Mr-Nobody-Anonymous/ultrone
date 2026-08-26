# Copyright (c) Ultrone Contributors. All rights reserved.
"""Scenario system + runner: ties every simulation layer together.

    clock -> environment -> events -> scheduler -> UCL platforms
          -> telemetry -> evaluation -> checkpoints

A :class:`Scenario` is a running instance built from a
:class:`ScenarioSpec`; ``build_default_scenario(seed)`` provides a
multi-domain baseline covering air/land/sea/cyber/facility tasks.
Execution is sequential discrete-event style: each dispatched task runs
to completion in fast time, and the shared clock jumps accordingly.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List

from sandbox.ucl import SimulationLab
from simulation.core import (
    Evaluator,
    EventBus,
    Scheduler,
    ScheduledTask,
    SimulationClock,
    TelemetryRecorder,
)
from simulation.world import Contact, EnvironmentModel, SensorSuite, Weather


# --------------------------------------------------------------------- #
# Scenario spec                                                          #
# --------------------------------------------------------------------- #
@dataclass(frozen=True)
class TaskSpec:
    platform_id: str
    task: Dict[str, Any]
    start_tick: int = 0
    priority: int = 1


@dataclass(frozen=True)
class EventSpec:
    tick: int
    name: str
    action: str                       # "weather_shift" | "log"
    params: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ScenarioSpec:
    name: str
    seed: int
    tasks: Tuple[TaskSpec, ...]
    events: Tuple[EventSpec, ...] = ()
    duration_ticks: int = 1000
    base_wind: float = 6.0
    cloud_cover: float = 0.3


def build_default_scenario_spec(seed: int = 0) -> ScenarioSpec:
    """Multi-domain baseline: one meaningful task per domain."""
    return ScenarioSpec(
        name="baseline_multi_domain",
        seed=seed,
        tasks=(
            TaskSpec("uav-1", {"type": "navigate", "to": [12.0, 10.0]},
                     start_tick=0),
            TaskSpec("ugv-1", {"type": "navigate", "to": [8.0, 6.0]},
                     start_tick=1),
            TaskSpec("cyber-1", {"type": "scan"}, start_tick=2),
            TaskSpec("conv-1", {"type": "produce", "quantity": 12},
                     start_tick=4),
            TaskSpec("cnc-1", {"type": "produce", "quantity": 4},
                     start_tick=6),
        ),
        events=(EventSpec(30, "wind_pickup", "weather_shift",
                          {"base_wind": 9.0}),),
    )


# --------------------------------------------------------------------- #
# Built-in event actions                                                 #
# --------------------------------------------------------------------- #
_EVENT_ACTIONS: Dict[str, Callable[[Any, Dict[str, Any]], None]] = {}


def event_action(name: str):
    def register(fn):
        _EVENT_ACTIONS[name] = fn
        return fn
    return register


@event_action("weather_shift")
def _weather_shift(scenario, params: Dict[str, Any]) -> None:
    if "base_wind" in params:
        scenario.env.weather.base_wind = float(params["base_wind"])
    if "cloud_cover" in params:
        scenario.env.weather.cloud_cover = float(params["cloud_cover"])


@event_action("log")
def _log(scenario, params: Dict[str, Any]) -> None:
    scenario.event_log.append(dict(params))


# --------------------------------------------------------------------- #
# Running scenario                                                       #
# --------------------------------------------------------------------- #
class Scenario:
    """One running simulation: clock + env + events + scheduler + UCL."""

    def __init__(self, spec: ScenarioSpec) -> None:
        self.spec = spec
        self.lab = SimulationLab(seed=spec.seed)
        self.clock = SimulationClock()
        self.env = EnvironmentModel(
            seed=spec.seed,
            weather=Weather(base_wind=spec.base_wind,
                            cloud_cover=spec.cloud_cover))
        self.bus = EventBus()
        self.scheduler = Scheduler()
        self.telemetry = TelemetryRecorder()
        self.suite = SensorSuite(self.env, seed=spec.seed)
        self.event_log: List[Dict[str, Any]] = []
        self.contacts: List[Contact] = [
            Contact("buoy-alpha", "buoy", 10.0, 4.0),
            Contact("buoy-beta", "buoy", 16.0, 12.0),
        ]

        for ev in spec.events:
            action = _EVENT_ACTIONS.get(ev.action)
            if action is not None:
                params = dict(ev.params)
                self.bus.schedule(
                    ev.tick, ev.name,
                    lambda scn, fn=action, p=params: fn(scn, p))

        for ts in sorted(spec.tasks,
                         key=lambda t: (t.start_tick, -t.priority)):
            self.scheduler.enqueue(ScheduledTask(
                platform_id=ts.platform_id, task=dict(ts.task),
                start_tick=ts.start_tick, priority=ts.priority))

    # -- execution ---------------------------------------------------------- #
    def run(self) -> Dict[str, Any]:
        completed: List[Dict[str, Any]] = []
        guard = 0
        while self.scheduler.pending > 0 and guard < 5000:
            guard += 1
            self.env.update(self.clock.tick)
            self.bus.fire_due(self.clock.tick, self)

            due = self.scheduler.pop_due(self.clock.tick)
            if not due:
                self._idle_step()
                continue

            for scheduled in due:
                controller = self.lab.controller(scheduled.platform_id)
                result = controller.execute_task(scheduled.task,
                                                 max_ticks=400)
                used = int(result.get("ticks_used", 1))
                self.clock.advance(max(1, used))
                self.env.update(self.clock.tick)
                completed.append({
                    "platform_id": scheduled.platform_id,
                    "task_type": scheduled.task.get("type"),
                    "start_tick": scheduled.start_tick,
                    "finished_tick": self.clock.tick,
                    **result,
                })
                self.telemetry.record(
                    self.clock.tick,
                    states={pid: c.get_state()
                            for pid, c in self.lab.controllers.items()},
                    extra={"last_task_platform": scheduled.platform_id},
                )

        energy = sum(float(r.get("energy_proxy", 0)) for r in completed)
        evaluation = Evaluator.evaluate(
            [{"success": bool(r.get("success"))} for r in completed],
            hard_violations=self.lab.hard_violations(),
            energy_used=energy,
        )
        return {
            "scenario": self.spec.name,
            "seed": self.spec.seed,
            "tasks": completed,
            "evaluation": evaluation,
            "events_fired": list(self.bus.fired_log),
            "telemetry_fingerprint": self.telemetry.fingerprint(),
        }

    def _idle_step(self) -> None:
        next_start = min((t.start_tick for t in self.scheduler.queue),
                         default=self.clock.tick + 1)
        step_to = max(self.clock.tick + 1,
                      min(next_start, self.clock.tick + 50))
        while self.clock.tick < step_to:
            self.env.update(self.clock.advance())
            self.lab.machine_controller.step_all(self.clock.tick)
            self._sync_world_clock()

    def _sync_world_clock(self) -> None:
        wm = self.lab.world
        while wm.environment["tick"] < self.clock.tick:
            wm.advance_tick()


def build_default_scenario(seed: int = 0) -> Scenario:
    return Scenario(build_default_scenario_spec(seed))