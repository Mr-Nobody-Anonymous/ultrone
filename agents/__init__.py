# Copyright (c) Ultrone Contributors. All rights reserved.
"""Agent modules for all domains."""

# Air domain agents
from .air.drone_agent import DroneAgent
from .air.fighter_agent import FighterAgent
from .air.missile_agent import MissileAgent

# Land domain agents
from .land.tank_agent import TankAgent
from .land.infantry_agent import InfantryAgent
from .land.mobile_missile_agent import MobileMissileAgent

# Sea domain agents
from .sea.vessel_agent import VesselAgent
from .sea.submarine_agent import SubmarineAgent
from .sea.naval_air_agent import NavalAirAgent

# Cyber domain agents
from .cyber.recon_agent import ReconAgent
from .cyber.exploit_agent import ExploitAgent
from .cyber.defend_agent import DefendAgent

# Space domain agents
from .space.satellite_agent import SatelliteAgent
from .space.orbital_agent import OrbitalAgent
from .space.space_weapon_agent import SpaceWeaponAgent

# Base agent
from .base_agent import BaseAgent

__all__ = [
    # Base
    "BaseAgent",
    # Air
    "DroneAgent", "FighterAgent", "MissileAgent",
    # Land
    "TankAgent", "InfantryAgent", "MobileMissileAgent",
    # Sea
    "VesselAgent", "SubmarineAgent", "NavalAirAgent",
    # Cyber
    "ReconAgent", "ExploitAgent", "DefendAgent",
    # Space
    "SatelliteAgent", "OrbitalAgent", "SpaceWeaponAgent",
]