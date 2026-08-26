# Copyright (c) Ultrone Contributors. All rights reserved.
"""Factory registration for civilian machine-operator agents."""

from __future__ import annotations

import logging
from typing import Optional

from agents.civilian.crane_operator import CraneOperatorAgent
from agents.civilian.drone_logistics import DeliveryDroneAgent
from agents.civilian.inspection_robot import InspectionRobotAgent
from agents.civilian.machinist import MachiningAgent
from agents.civilian.process_operator import ProcessOperatorAgent
from agents.civilian.warehouse_arm import WarehouseArmAgent
from agents.civilian.universal_operator import UniversalOperatorAgent
from agents.registry import AgentRegistry
from data.entities import DomainType

logger = logging.getLogger("Ultrone.Agents.Civilian.Factory")

#: Descriptions advertise exactly what these agents are -- and are not.
_CIVILIAN_TYPES = (
    ("inspection_robot", InspectionRobotAgent,
     "Simulated mobile robot for waypoint inspection patrols "
     "(civilian facility automation; non-weaponized)"),
    ("warehouse_arm", WarehouseArmAgent,
     "Simulated robotic arm for warehouse pick/place positioning "
     "(civilian automation; non-weaponized)"),
    ("process_operator", ProcessOperatorAgent,
     "Simulated operator for tanks, conveyors, and climate units "
     "(civilian process control; non-weaponized)"),
    ("crane_operator", CraneOperatorAgent,
     "Simulated overhead-crane operator with anti-sway load handling "
     "(civilian logistics; non-weaponized)"),
    ("cnc_machinist", MachiningAgent,
     "Simulated CNC machinist with door interlock and tool lifecycle "
     "(civilian manufacturing; non-weaponized)"),
    ("drone_logistics", DeliveryDroneAgent,
     "Simulated battery-aware delivery drone honoring no-fly zones "
     "(civilian parcel logistics; non-weaponized)"),
    ("universal_operator", UniversalOperatorAgent,
     "Kind-agnostic simulated operator that discovers capabilities at "
     "runtime and drives ANY registered machine through the interlocked "
     "dispatch interface (civilian automation; non-weaponized)"),
)


def register_civilian_agents(registry: Optional[AgentRegistry] = None) -> None:
    if registry is None:
        from agents.registry import _default_registry

        registry = _default_registry
    for agent_type, agent_class, description in _CIVILIAN_TYPES:
        registry.register(
            agent_type=agent_type,
            agent_class=agent_class,
            domain=DomainType.GENERAL,
            description=description,
            capabilities=["sense", "communicate"],   # never "engage"
        )
    logger.info("Civilian machine-operator agents registered")


# Auto-register on import (same convention as other domains).
register_civilian_agents()
