# Copyright (c) Ultrone Contributors. All rights reserved.
"""Civilian machine-operator agents (simulation-only).

This domain contains NON-MILITARY machine operators -- warehouse,
inspection, and facility-control agents driving the deterministic sandbox
machines in ``sandbox/machines.py``.

Hard design rules:

1. Capabilities are ``[SENSE, COMMUNICATE]`` only -- the ENGAGE capability
   is deliberately absent from every class in this package and this is
   enforced by test.
2. Every actuated command passes through the machine's SafetyInterlock;
   out-of-envelope commands are refused and recorded.
3. Missions are industrial setpoint/patrol/throughput tasks evaluated
   inside the simulation. Nothing here interfaces with real hardware.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from agents.base_agent import AgentCapability, BaseAgent
from data.entities import DomainType

#: Civilian operators sense and report; they never engage.
CIVILIAN_CAPABILITIES = [AgentCapability.SENSE, AgentCapability.COMMUNICATE]


class CivilianMachineAgent(BaseAgent):
    """Base class for simulated civilian machine operators."""

    MACHINE_KIND = "machine"

    def __init__(
        self,
        unit_id: str,
        position: tuple = (0.0, 0.0, 0.0),
        controller: Optional[Any] = None,
        seed: int = 0,
        **kwargs: Any,
    ) -> None:
        super().__init__(
            unit_id=unit_id,
            domain=DomainType.GENERAL,
            unit_type=self.MACHINE_KIND,
            position=position,
            team="civilian",
            capabilities=list(CIVILIAN_CAPABILITIES),
            **kwargs,
        )
        if controller is None:
            from sandbox.machines import MachineController

            controller = MachineController(seed=seed)
        self.controller = controller
        self.interlock = controller.interlock
        self.machine = None                 # attached by subclasses
        self.mission_log: List[Dict[str, Any]] = []

    # -- wiring -------------------------------------------------------------- #
    def attach_machine(self, machine) -> None:
        """Register the sandbox machine this operator drives."""
        self.controller.register(machine)
        self.machine = machine

    # -- framework ------------------------------------------------------------- #
    def take_turn(self, world_state: Any,
                  messages: List[Any]) -> List[Any]:
        tick = world_state.get("tick", 0) if isinstance(world_state, dict) else 0
        self.controller.step_all(tick)
        replies: List[Any] = []
        for message in messages:
            reply = self.handle_message(message)
            if reply is not None:
                replies.append(reply)
        return replies

    def _log_mission(self, mission_type: str, result: Dict[str, Any]) -> None:
        entry = {"mission": mission_type, "success": result.get("success", False)}
        entry.update({k: v for k, v in result.items() if k != "success"})
        self.mission_log.append(entry)

    @staticmethod
    def _steer_toward(x: float, y: float, heading: float,
                      tx: float, ty: float) -> tuple:
        import math

        dx, dy = tx - x, ty - y
        dist = math.hypot(dx, dy)
        turn = (math.atan2(dy, dx) - heading + math.pi) % (2 * math.pi) - math.pi
        return dist, max(-1.0, min(1.0, turn * 2.0))
