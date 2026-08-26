# Copyright (c) Ultrone Contributors. All rights reserved.
"""Subsystem-level platform control for every simulated machine agent.

``SubsystemControlledAgent`` composes a machine from subsystem objects and
gives higher-level AI one uniform control surface regardless of platform
kind::

    agent.execute(Command("propulsion", "set_throttle", {"value": 0.65}))
    agent.execute(Command("navigation", "set_destination",
                          {"position": [10.0, 5.0]}))
    agent.available_capabilities()      # pruned hierarchical tree
    agent.platform_state.get()          # unified snapshot
    agent.tick_platform(tick)           # deterministic dynamics step

Every domain has a default subsystem composition (see
``DOMAIN_SUBSYSTEM_FACTORIES``); specialized platforms override
``_build_subsystems`` -- a submarine adds ballast and sonar, a satellite
keeps orbital navigation, a computing node carries defensive controls.

Determinism: sensor seeds derive from ``zlib.crc32(unit_id)`` so identical
configurations reproduce identically across runs.

Simulation boundary: the command system models detailed operation of
sandboxed simulated platforms only -- there is intentionally no interface,
and no path, toward operating real-world weapons, vehicles, infrastructure,
or computer systems.
"""

from __future__ import annotations

import zlib
from typing import Any, Callable, Dict, List

from agents.base_agent import BaseAgent
from agents.capabilities import HierarchicalCapabilitySet
from agents.commands import Command, CommandBus, CommandResult
from agents.state import PlatformStateView
from agents.telemetry import TelemetryRecorder
from data.entities import DomainType


# --------------------------------------------------------------------- #
# Per-domain default compositions                                        #
# --------------------------------------------------------------------- #
def _stable_seed(unit_id: str) -> int:
    return zlib.crc32(str(unit_id).encode()) % 100_000


def _air_platform(seed: int = 0) -> list:
    from agents.subsystems.flight import FlightControlSubsystem
    from agents.subsystems.platform_subsystems import (
        AutonomySubsystem, CommunicationSubsystem, EnvironmentSubsystem,
        HealthSubsystem, NavigationSubsystem, PayloadSubsystem,
        PowerSubsystem, PropulsionSubsystem, SensorSubsystem)

    return [
        PropulsionSubsystem(fuel_capacity=80.0),
        NavigationSubsystem(),
        FlightControlSubsystem(),
        SensorSubsystem(seed=seed),
        CommunicationSubsystem(),
        PowerSubsystem(generation_kw=3.0),
        PayloadSubsystem(capacity_kg=25.0),
        HealthSubsystem(wear_rate=0.02),
        EnvironmentSubsystem(),
        AutonomySubsystem(),
    ]


def _land_platform(seed: int = 0) -> list:
    from agents.subsystems.mobility import MobilitySubsystem
    from agents.subsystems.platform_subsystems import (
        AutonomySubsystem, CommunicationSubsystem, HealthSubsystem,
        NavigationSubsystem, PowerSubsystem, PropulsionSubsystem,
        SensorSubsystem)

    return [
        PropulsionSubsystem(fuel_capacity=120.0),
        MobilitySubsystem(max_speed=2.5),
        NavigationSubsystem(),
        SensorSubsystem(seed=seed),
        CommunicationSubsystem(),
        PowerSubsystem(),
        HealthSubsystem(wear_rate=0.04),
        AutonomySubsystem(),
    ]


def _sea_platform(seed: int = 0) -> list:
    from agents.subsystems.platform_subsystems import (
        AutonomySubsystem, CommunicationSubsystem, HealthSubsystem,
        NavigationSubsystem, PayloadSubsystem, PowerSubsystem,
        PropulsionSubsystem, SensorSubsystem)

    return [
        PropulsionSubsystem(fuel_capacity=150.0),
        NavigationSubsystem(),
        SensorSubsystem(seed=seed),
        CommunicationSubsystem(),
        PowerSubsystem(generation_kw=4.0),
        PayloadSubsystem(capacity_kg=200.0),
        HealthSubsystem(wear_rate=0.02),
        AutonomySubsystem(),
    ]


def _space_platform(seed: int = 0) -> list:
    from agents.subsystems.diagnostics import DiagnosticsSubsystem
    from agents.subsystems.orbital import OrbitalNavigationSubsystem
    from agents.subsystems.platform_subsystems import (
        AttitudeSubsystem, AutonomySubsystem, CommunicationSubsystem,
        HealthSubsystem, NavigationSubsystem, PayloadSubsystem,
        PowerSubsystem, SensorSubsystem, ThermalSubsystem)

    diagnostics = DiagnosticsSubsystem()
    subsystems = [
        PowerSubsystem(generation_kw=5.0),
        ThermalSubsystem(),
        AttitudeSubsystem(),
        NavigationSubsystem(),
        OrbitalNavigationSubsystem(),
        SensorSubsystem(seed=seed),
        CommunicationSubsystem(),
        PayloadSubsystem(capacity_kg=50.0),
        HealthSubsystem(wear_rate=0.01),
        AutonomySubsystem(),
        diagnostics,
    ]
    # Fault management: the diagnostics sweep watches every sibling.
    for subsystem in subsystems[:-1]:
        diagnostics.register_component(subsystem)
    return subsystems


def _cyber_platform(seed: int = 0) -> list:
    from agents.subsystems.computing import (
        AuthenticationSubsystem, ComputeSubsystem, ConfigurationSubsystem,
        DefensiveControlsSubsystem, MonitoringSubsystem,
        NetworkInterfaceSubsystem, ServiceSubsystem, StorageSubsystem)
    from agents.subsystems.platform_subsystems import HealthSubsystem

    return [
        ComputeSubsystem(),
        StorageSubsystem(),
        NetworkInterfaceSubsystem(),
        ServiceSubsystem(),
        AuthenticationSubsystem(),
        MonitoringSubsystem(),
        ConfigurationSubsystem(),
        DefensiveControlsSubsystem(),
        HealthSubsystem(wear_rate=0.005),
    ]


def _general_platform(seed: int = 0) -> list:
    from agents.subsystems.platform_subsystems import (
        AutonomySubsystem, CommunicationSubsystem, HealthSubsystem,
        NavigationSubsystem, PowerSubsystem, SensorSubsystem)

    return [
        NavigationSubsystem(),
        SensorSubsystem(seed=seed),
        CommunicationSubsystem(),
        PowerSubsystem(),
        HealthSubsystem(wear_rate=0.02),
        AutonomySubsystem(),
    ]


DOMAIN_SUBSYSTEM_FACTORIES: Dict[DomainType, Callable[..., list]] = {
    DomainType.AIR: _air_platform,
    DomainType.LAND: _land_platform,
    DomainType.SEA: _sea_platform,
    DomainType.SPACE: _space_platform,
    DomainType.CYBER: _cyber_platform,
    DomainType.GENERAL: _general_platform,
}

# Hierarchical capability leaves advertised per domain (validated against
# agents.capabilities.CAPABILITY_TREE).
DOMAIN_CAPABILITY_LEAVES: Dict[DomainType, tuple] = {
    DomainType.AIR: ("translation", "rotation", "altitude", "visual",
                     "thermal", "navigation_sensors", "generation",
                     "storage", "transmit", "receive", "diagnostics",
                     "faults", "navigation", "observation",
                     "task_execution"),
    DomainType.LAND: ("translation", "rotation", "visual", "acoustic",
                      "generation", "storage", "transmit", "receive",
                      "diagnostics", "faults", "navigation",
                      "observation", "task_execution"),
    DomainType.SEA: ("translation", "depth", "visual", "acoustic",
                     "generation", "storage", "transmit", "receive",
                     "diagnostics", "faults", "navigation",
                     "observation", "task_execution"),
    DomainType.SPACE: ("orbital_motion", "rotation", "altitude",
                       "thermal", "simulated_electromagnetic",
                       "generation", "storage", "transmit", "receive",
                       "diagnostics", "faults", "navigation",
                       "observation", "task_execution"),
    DomainType.CYBER: ("simulated_electromagnetic", "routing",
                       "transmit", "receive", "distribution", "storage",
                       "diagnostics", "faults", "task_execution"),
}


class SubsystemControlledAgent(BaseAgent):
    """BaseAgent + composed subsystems behind a structured CommandBus.

    Additive to classic agent behavior: ``take_turn`` /
    ``execute_mission`` semantics are unchanged; subclasses additionally
    gain detailed subsystem operation through ``execute(Command)``.
    """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.bus = CommandBus()
        self.telemetry_recorder = TelemetryRecorder(
            source_id=self.unit.unit_id)
        self.capability_tree = HierarchicalCapabilitySet(
            self._capability_leaves())
        for subsystem in self._build_subsystems():
            self.register_subsystem(subsystem)

    # -- composition hooks -------------------------------------------------- #
    def _capability_leaves(self) -> tuple:
        """Capability leaves; override for specialized platforms."""
        return DOMAIN_CAPABILITY_LEAVES.get(
            getattr(self.unit, "domain", DomainType.GENERAL), ())

    def _build_subsystems(self) -> List[Any]:
        seed = _stable_seed(self.unit.unit_id)
        factory = DOMAIN_SUBSYSTEM_FACTORIES.get(
            getattr(self.unit, "domain", DomainType.GENERAL))
        return factory(seed=seed) if factory else []

    # -- wiring / control ------------------------------------------------------ #
    def register_subsystem(self, subsystem) -> Any:
        self.bus.register(subsystem)
        # Bind well-known handles: agent.<subsystem-name> -> instance,
        # unless a subclass already manages that attribute itself.
        if not hasattr(self, subsystem.name):
            setattr(self, subsystem.name, subsystem)
        return subsystem

    def execute(self, command: Command) -> CommandResult:
        # Enforcement of engaged safety interlocks happens inside the
        # CommandBus itself, so this thin wrapper is the SAME path the
        # UCL uses -- one gate, one mechanism, zero divergence.
        result = self.bus.execute(command)
        self.telemetry_recorder.record_command(result)
        return result

    def get_subsystem(self, name: str) -> Any:
        return self.bus.get(name)

    def subsystem_names(self) -> List[str]:
        return self.bus.names()

    # -- views ------------------------------------------------------------------ #
    def available_capabilities(self) -> Dict[str, Any]:
        """Pruned hierarchical capability tree for this platform."""
        return self.capability_tree.available()

    @property
    def platform_state(self) -> PlatformStateView:
        """Unified read model over every registered subsystem."""
        return PlatformStateView(self.bus)

    def state_snapshot(self, tick: int = 0) -> Dict[str, Any]:
        snapshot = self.platform_state.get(tick)
        self.telemetry_recorder.record_snapshot(snapshot, tick)
        return snapshot

    # -- dynamics ------------------------------------------------------------- #
    def tick_platform(self, tick: int) -> None:
        """Advance every subsystem one deterministic tick; record state."""
        for name in self.subsystem_names():
            self.bus.get(name).tick(tick)
        self.state_snapshot(tick)

    def command_history(self) -> List[Dict[str, Any]]:
        return self.telemetry_recorder.commands()
