# Copyright (c) Ultrone Contributors. All rights reserved.
"""Simulation clock with tick-based timing and acceleration."""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Callable, Optional
from enum import Enum

logger = logging.getLogger("Ultrone.Sim.Clock")


class AccelerationFactor(Enum):
    """Simulation speed multipliers."""
    PAUSE = 0
    REAL_TIME = 1
    FAST_2X = 2
    FAST_5X = 5
    FAST_10X = 10
    FAST_100X = 100


class SimulationClock:
    """
    Ticks-based simulation clock with pause and acceleration.
    
    Controls the timing of the simulation loop.
    """
    
    def __init__(
        self,
        tick_duration_seconds: float = 1.0,
        acceleration: AccelerationFactor = AccelerationFactor.FAST_10X,
        start_time: Optional[datetime] = None,
    ):
        self.tick_duration = tick_duration_seconds
        self.acceleration = acceleration
        self.sim_time = start_time or datetime.utcnow()
        self.real_start = datetime.utcnow()
        self.tick_count = 0
        self._running = False
        self._tick_callbacks: list = []
        self._on_tick_callback: Optional[Callable] = None
    
    def tick(self) -> 'SimulationClock':
        """Advance simulation by one tick. Returns self for chaining."""
        self.tick_count += 1
        if self.acceleration != AccelerationFactor.PAUSE:
            self.sim_time += timedelta(seconds=self.tick_duration * self.acceleration.value)
        return self
    
    def get_sim_time(self) -> datetime:
        """Get current simulation time."""
        return self.sim_time
    
    def get_real_elapsed(self) -> float:
        """Get real elapsed time in seconds."""
        return (datetime.utcnow() - self.real_start).total_seconds()
    
    def get_tick_count(self) -> int:
        """Get total tick count."""
        return self.tick_count
    
    def set_acceleration(self, factor: AccelerationFactor) -> None:
        """Set simulation speed."""
        self.acceleration = factor
        logger.info(f"Clock acceleration set to {factor.name}")
    
    def pause(self) -> None:
        """Pause the simulation."""
        self.acceleration = AccelerationFactor.PAUSE
    
    def resume(self) -> None:
        """Resume simulation at real-time speed."""
        self.acceleration = AccelerationFactor.REAL_TIME
    
    def register_tick_callback(self, callback: Callable) -> None:
        """Register a callback for each tick."""
        self._tick_callbacks.append(callback)
    
    async def wait_for_tick(self) -> None:
        """Wait for the appropriate real time based on acceleration."""
        if self.acceleration == AccelerationFactor.PAUSE:
            return
        # The simulation runs as fast as possible, but we can throttle
        if self.acceleration == AccelerationFactor.REAL_TIME:
            await asyncio.sleep(self.tick_duration)