# Copyright (c) Ultrone Contributors. All rights reserved.
"""Simulated machine subsystems: compose platforms from parts."""

from agents.subsystems.base import Subsystem, command
from agents.subsystems.computing import (
    AuthenticationSubsystem,
    ComputeSubsystem,
    ConfigurationSubsystem,
    DefensiveControlsSubsystem,
    MonitoringSubsystem,
    NetworkInterfaceSubsystem,
    ServiceSubsystem,
    StorageSubsystem,
)
from agents.subsystems.diagnostics import DiagnosticsSubsystem
from agents.subsystems.faults import FaultInjector
from agents.subsystems.flight import FlightControlSubsystem
from agents.subsystems.life_support import LifeSupportSubsystem
from agents.subsystems.locomotion import MobilitySubsystem
from agents.subsystems.naval import BallastSubsystem, SonarSubsystem
from agents.subsystems.orbital import OrbitalNavigationSubsystem
from agents.subsystems.safety import SafetyInterlockSubsystem
from agents.subsystems.platform_subsystems import (
    AttitudeSubsystem,
    AutonomySubsystem,
    CommunicationSubsystem,
    EnvironmentSubsystem,
    HealthSubsystem,
    NavigationSubsystem,
    PayloadSubsystem,
    PowerSubsystem,
    PropulsionSubsystem,
    ResourceSubsystem,
    SensorSubsystem,
    ThermalSubsystem,
)

__all__ = [
    "Subsystem", "command", "FaultInjector",
    # Core platform subsystems
    "PropulsionSubsystem", "PowerSubsystem", "NavigationSubsystem",
    "SensorSubsystem", "CommunicationSubsystem", "PayloadSubsystem",
    "HealthSubsystem", "AutonomySubsystem", "ThermalSubsystem",
    "AttitudeSubsystem", "EnvironmentSubsystem", "ResourceSubsystem",
    # Extended subsystems
    "FlightControlSubsystem", "MobilitySubsystem",
    "BallastSubsystem", "SonarSubsystem", "OrbitalNavigationSubsystem",
    "LifeSupportSubsystem", "DiagnosticsSubsystem",
    "SafetyInterlockSubsystem",
    # Computing-node subsystems
    "ComputeSubsystem", "StorageSubsystem", "NetworkInterfaceSubsystem",
    "ServiceSubsystem", "AuthenticationSubsystem", "MonitoringSubsystem",
    "ConfigurationSubsystem", "DefensiveControlsSubsystem",
]