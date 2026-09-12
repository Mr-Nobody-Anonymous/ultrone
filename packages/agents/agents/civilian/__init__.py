# Copyright (c) Ultrone Contributors. All rights reserved.
"""Civilian machine-operator domain (simulation-only, non-weaponized).

See ``agents/civilian/base.py`` for the design rules. Importing this
package auto-registers its agent types in the global registry under
``DomainType.GENERAL``.
"""

from agents.civilian.base import CIVILIAN_CAPABILITIES, CivilianMachineAgent
from agents.civilian.crane_operator import CraneOperatorAgent
from agents.civilian.domain_operators import (
    NetworkAnalystAgent,
    RailOperatorAgent,
    SatelliteOpsAgent,
    VesselOperatorAgent,
)
from agents.civilian.drone_logistics import DeliveryDroneAgent
from agents.civilian.energy_operator import EnergyOperatorAgent
from agents.civilian.facility_coordinator import FacilityCoordinatorAgent
from agents.civilian.factory import register_civilian_agents
from agents.civilian.inspection_robot import InspectionRobotAgent
from agents.civilian.machinist import MachiningAgent
from agents.civilian.process_operator import ProcessOperatorAgent
from agents.civilian.subsystem_platforms import (
    DeliveryTruckAgent,
    SurveyAircraftAgent,
)
from agents.civilian.universal_operator import UniversalOperatorAgent
from agents.civilian.water_operator import WaterOperatorAgent
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
    "EnergyOperatorAgent",
    "WaterOperatorAgent",
    "FacilityCoordinatorAgent",
    "UniversalOperatorAgent",
    "VesselOperatorAgent",
    "RailOperatorAgent",
    "SatelliteOpsAgent",
    "NetworkAnalystAgent",
    "SurveyAircraftAgent",
    "DeliveryTruckAgent",
    "register_civilian_agents",
]
