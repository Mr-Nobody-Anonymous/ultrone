"""Robot interface abstractions."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
import numpy as np

@dataclass
class RobotState:
    position: np.ndarray = field(default_factory=lambda: np.zeros(3))
    orientation: np.ndarray = field(default_factory=lambda: np.zeros(4))
    velocity: np.ndarray = field(default_factory=lambda: np.zeros(3))
    joints: Dict[str, float] = field(default_factory=dict)
    sensors: Dict[str, Any] = field(default_factory=dict)

class RobotInterface:
    name: str = "base"
    def __init__(self) -> None:
        self._state = RobotState()
        self._connected = False
    def connect(self) -> bool:
        self._connected = True
        return True
    def disconnect(self) -> None:
        self._connected = False
    def get_state(self) -> RobotState:
        return self._state
    def send_command(self, command: str, **kwargs: Any) -> bool:
        return True
    @property
    def is_connected(self) -> bool:
        return self._connected
