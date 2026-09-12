# Copyright (c) Ultrone Contributors. All rights reserved.
"""Robotic platform agents composed from simulated subsystems.

Civilian-grade robots (ground / aerial / underwater / industrial) built
entirely from the shared subsystem library and driven exclusively through
the structured Command interface::

    robot.execute(Command("mobility", "drive", {"speed": 1.0}))

Hard design rules (enforced by test):

1. Capabilities are ``[SENSE, COMMUNICATE]`` only -- no ENGAGE anywhere.
2. All actuation flows through the platform's CommandBus and its
   interlock-friendly subsystems; out-of-envelope commands fail cleanly.
3. Everything here operates sandboxed simulation state exclusively;
   nothing interfaces with real hardware.
"""

from __future__ import annotations

import math
from typing import Any, Callable, Dict, List, Optional, Tuple

from agents.base_agent import AgentCapability
from agents.commands import Command
from agents.platform_agent import SubsystemControlledAgent
from data.entities import DomainType

#: Robotic platforms sense and report; they never engage.
ROBOT_CAPABILITIES = [AgentCapability.SENSE, AgentCapability.COMMUNICATE]

ROBOT_LEAVES = ("translation", "storage", "generation", "transmit",
                "receive", "diagnostics", "faults", "navigation",
                "observation", "task_execution")


class RoboticPlatformAgent(SubsystemControlledAgent):
    """Common wiring for every robotics-domain platform agent."""

    MACHINE_KIND = "robot"

    def __init__(self, unit_id: str, **kwargs: Any) -> None:
        kwargs.setdefault("position", (0.0, 0.0, 0.0))
        kwargs.setdefault("team", "civilian")
        super().__init__(
            unit_id=unit_id,
            domain=DomainType.GENERAL,
            unit_type=self.MACHINE_KIND,
            capabilities=list(ROBOT_CAPABILITIES),
            **kwargs,
        )

    def _capability_leaves(self) -> tuple:
        return ROBOT_LEAVES

    # -- framework --------------------------------------------------------- #
    def take_turn(self, world_state: Any,
                  messages: List[Any]) -> List[Any]:
        tick = world_state.get("tick", 0) if isinstance(world_state, dict) else 0
        self.tick_platform(tick)
        replies: List[Any] = []
        for message in messages:
            reply = self.handle_message(message)
            if reply is not None:
                replies.append(reply)
        return replies

    # -- shared transit helper ------------------------------------------------ #
    def _transit(self, tx: float, ty: float, speed_source: Callable[[], float],
                 max_ticks: int = 300) -> Tuple[bool, int]:
        """Steer the platform toward (tx, ty); returns (arrived, ticks)."""
        nav = self.get_subsystem("navigation")
        for tick in range(1, max_ticks):
            dist = math.hypot(tx - nav.x, ty - nav.y)
            if dist <= 0.5:
                return True, tick
            bearing = math.atan2(ty - nav.y, tx - nav.x)
            self.execute(Command("navigation", "set_heading",
                                 {"deg": math.degrees(bearing)}))
            speed = min(float(speed_source()), max(0.4, dist * 0.3))
            rad = math.radians(nav.heading_deg)
            nav.x += math.cos(rad) * speed
            nav.y += math.sin(rad) * speed
            self.tick_platform(tick)
        return math.hypot(tx - nav.x, ty - nav.y) <= 0.5, max_ticks

    @staticmethod
    def _waypoints(mission: Dict[str, Any]) -> List[Tuple[float, float]]:
        return [(float(x), float(y))
                for x, y in mission.get("waypoints", [])]
