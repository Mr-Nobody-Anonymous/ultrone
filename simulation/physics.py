"""Physics engine for simulation."""
from __future__ import annotations
from typing import Any, Dict, List, Optional
import numpy as np

class PhysicsEngine:
    def __init__(self, gravity: float = 9.81, dt: float = 0.01) -> None:
        self.gravity = gravity
        self.dt = dt
        self._bodies: List[Dict[str, Any]] = []
    def add_body(self, mass: float, position: List[float], velocity: List[float] = None) -> int:
        bid = len(self._bodies)
        self._bodies.append({
            "id": bid, "mass": mass,
            "position": np.array(position, dtype=np.float64),
            "velocity": np.array(velocity or [0.0]*len(position), dtype=np.float64),
        })
        return bid
    def step(self) -> None:
        for body in self._bodies:
            body["velocity"][2] -= self.gravity * self.dt
            body["position"] += body["velocity"] * self.dt
    def get_position(self, body_id: int) -> np.ndarray:
        return self._bodies[body_id]["position"].copy()
    @property
    def body_count(self) -> int:
        return len(self._bodies)
