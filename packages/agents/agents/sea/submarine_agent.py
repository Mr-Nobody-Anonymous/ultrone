# Copyright (c) Ultrone Contributors. All rights reserved.
"""Submarine agent - underwater warfare operations."""

from __future__ import annotations

import logging
from typing import Dict, List, Any

from agents.base_agent import BaseAgent
from agents.platform_agent import SubsystemControlledAgent
from agents.subsystems.naval import BallastSubsystem, SonarSubsystem
from data.entities import DomainType, AgentState, Contact

logger = logging.getLogger("Ultrone.Agents.Sea.Submarine")


class SubmarineAgent(SubsystemControlledAgent):
    """Submarine agent specializing in underwater warfare, ASW, and stealth operations.

    Composed on the SEA subsystem default set plus naval extras: a
    :class:`BallastSubsystem` for depth control and a :class:`SonarSubsystem`
    for passive/active acoustic sensing -- all driven through ``execute``.
    """

    def __init__(
        self,
        unit_id: str,
        position: tuple,
        team: str = "blue",
        message_bus=None,
    ):
        super().__init__(
            unit_id=unit_id,
            domain=DomainType.SEA,
            unit_type="submarine",
            position=position,
            team=team,
            message_bus=message_bus,
        )
        self.depth: float = 50.0  # Current depth in meters
        self.is_silent_running: bool = False
        self.torpedo_count: int = 12

        # Naval-specific subsystems layered onto the domain default set.
        self.ballast = BallastSubsystem(max_depth_m=300.0,
                                        initial_depth_m=self.depth)
        self.sonar = SonarSubsystem()
        self.register_subsystem(self.ballast)
        self.register_subsystem(self.sonar)

    def take_turn(self, world_state: Any, messages: List[Any]) -> List[Any]:
        """Execute submarine tactical behavior."""
        outbound: List[Any] = []

        # Silent running mode
        if self.unit.health < 0.5:
            self.is_silent_running = True
        else:
            self.is_silent_running = False

        return outbound

    def execute_mission(self, mission: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a submarine mission."""
        outcome = {"success": True, "unit_id": self.unit.unit_id}
        if mission.get("type") == "asw_patrol":
            logger.info(f"{self.unit.unit_id} conducting ASW patrol")
        elif mission.get("type") == "covert_insertion":
            logger.info(f"{self.unit.unit_id} conducting covert insertion")
            outcome["success"] = self.unit.health > 0.3
        return outcome

