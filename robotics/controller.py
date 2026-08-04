"""Robot motion controller."""
from __future__ import annotations
from typing import Any, List, Optional
import numpy as np
from .robot_interface import RobotInterface, RobotState

class RobotController:
    def __init__(self, robot: Optional[RobotInterface] = None) -> None:
        self._robot = robot
        self._trajectory: List[np.ndarray] = []
    def plan_path(self, start: np.ndarray, goal: np.ndarray, obstacles: Optional[List] = None) -> List[np.ndarray]:
        steps = 10
        self._trajectory = [start + (goal - start) * (i / steps) for i in range(steps + 1)]
        return self._trajectory
    def execute(self) -> bool:
        if self._robot is None:
            return False
        for waypoint in self._trajectory:
            self._robot.send_command("move", position=waypoint.tolist())
        return True
    @property
    def trajectory_length(self) -> int:
        return len(self._trajectory)
