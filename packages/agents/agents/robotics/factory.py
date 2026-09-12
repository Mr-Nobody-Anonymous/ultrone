# Copyright (c) Ultrone Contributors. All rights reserved.
"""Factory and registry wiring for robotics-domain platform agents."""

from __future__ import annotations

from typing import Any, Optional, Tuple

from agents.registry import AgentRegistry, _default_registry
from agents.robotics.aerial_robot_agent import AerialRobotAgent
from agents.robotics.ground_robot_agent import GroundRobotAgent
from agents.robotics.industrial_robot_agent import IndustrialRobotAgent
from agents.robotics.underwater_robot_agent import UnderwaterRobotAgent
from data.entities import DomainType


def register_robotics_agents(registry: Optional[AgentRegistry] = None
                             ) -> None:
    """Register every robotics platform with a global/default registry."""
    reg = registry or _default_registry
    registrations = (
        ("robot_ground", GroundRobotAgent,
         "Waypoint-patrol ground robot (simulation-only; non-weaponized)"),
        ("robot_aerial", AerialRobotAgent,
         "Small UAV inspection/delivery robot "
         "(simulation-only; non-weaponized)"),
        ("robot_underwater", UnderwaterRobotAgent,
         "Ballast-driven survey AUV (simulation-only; non-weaponized)"),
        ("robot_industrial", IndustrialRobotAgent,
         "Fixed-base manipulator for production cycles "
         "(simulation-only; non-weaponized)"),
    )
    for agent_type, agent_class, description in registrations:
        reg.register(
            agent_type=agent_type,
            agent_class=agent_class,
            domain=DomainType.GENERAL,
            description=description,
        )


def create_ground_robot(unit_id: str, position: Tuple[float, float,
                                                        float] = (0.0, 0.0, 0.0),
                        **kwargs: Any) -> GroundRobotAgent:
    return GroundRobotAgent(unit_id=unit_id, position=position, **kwargs)


def create_aerial_robot(unit_id: str, position: Tuple[float, float,
                                                      float] = (0.0, 0.0, 60.0),
                        **kwargs: Any) -> AerialRobotAgent:
    return AerialRobotAgent(unit_id=unit_id, position=position, **kwargs)


def create_underwater_robot(unit_id: str,
                            position: Tuple[float, float, float] =
                            (0.0, 0.0, -10.0),
                            **kwargs: Any) -> UnderwaterRobotAgent:
    return UnderwaterRobotAgent(unit_id=unit_id, position=position,
                                **kwargs)


def create_industrial_robot(unit_id: str,
                            position: Tuple[float, float, float] =
                            (0.0, 0.0, 0.0),
                            **kwargs: Any) -> IndustrialRobotAgent:
    return IndustrialRobotAgent(unit_id=unit_id, position=position,
                                **kwargs)


# Auto-register on import (mirrors the other domain factories).
register_robotics_agents()
