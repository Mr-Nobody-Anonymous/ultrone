# Copyright (c) Ultrone Contributors. All rights reserved.
"""Civilian machine-operator domain (simulation-only, non-weaponized).

See ``agents/civilian/base.py`` for the design rules. Importing this
package auto-registers its agent types in the global registry under
``DomainType.GENERAL``.
"""

from agents.civilian.base import CIVILIAN_CAPABILITIES, CivilianMachineAgent
from agents.civilian.crane_operator import CraneOperatorAgent
from agents.civilian.drone_logistics import DeliveryDroneAgent
from agents.civilian.factory import register_civilian_agents
from agents.civilian.inspection_robot import InspectionRobotAgent
from agents.civilian.machinist import MachiningAgent
from agents.civilian.process_operator import ProcessOperatorAgent
from agents.civilian.universal_operator import UniversalOperatorAgent
from agents.civilian.warehouse_arm import WarehouseArmAgent

__all__ = [
    "CIVILIAN_CAPABILITIES",
    "CivilianMachineAgent",
    "InspectionRobotAgent",
    "WarehouseArmAgent",
    "ProcessOperatorAgent",
    "CraneOperatorAgent",
    "MachiningAgent",
    "DeliveryDroneAgent",
    "UniversalOperatorAgent",
    "register_civilian_agents",
]
