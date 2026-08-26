# Copyright (c) Ultrone Contributors. All rights reserved.
"""Robotics-domain platform agents (simulation-only)."""

from agents.robotics.base import ROBOT_CAPABILITIES, RoboticPlatformAgent
from agents.robotics.factory import register_robotics_agents
from agents.robotics.ground_robot_agent import GroundRobotAgent
from agents.robotics.aerial_robot_agent import AerialRobotAgent
from agents.robotics.industrial_robot_agent import IndustrialRobotAgent
from agents.robotics.underwater_robot_agent import UnderwaterRobotAgent

__all__ = [
    "ROBOT_CAPABILITIES",
    "RoboticPlatformAgent",
    "GroundRobotAgent",
    "AerialRobotAgent",
    "UnderwaterRobotAgent",
    "IndustrialRobotAgent",
    "register_robotics_agents",
]
