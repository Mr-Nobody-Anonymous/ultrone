"""Simulation — Digital twin, physics, and environment generation."""
from .digital_twin import DigitalTwin, TwinConfig
from .physics import PhysicsEngine
from .environment_generator import EnvironmentGenerator
__all__ = ["DigitalTwin", "TwinConfig", "PhysicsEngine", "EnvironmentGenerator"]

# --- Multi-domain simulation framework (additive) ------------------------
from simulation.core import (  # noqa: E402
    CheckpointManager,
    Evaluator,
    EventBus,
    ExperimentRunner,
    ScheduledTask,
    Scheduler,
    SimulationClock,
    TelemetryRecorder,
)
from simulation.comms_logistics import (  # noqa: E402
    CommunicationNetwork,
    Depot,
    LogisticsSystem,
)
from simulation.runner import (  # noqa: E402
    EventSpec,
    Scenario,
    ScenarioSpec,
    TaskSpec,
    build_default_scenario,
    build_default_scenario_spec,
)
from simulation.world import (  # noqa: E402
    Contact,
    EnvironmentModel,
    SensorSuite,
)

__all__ += [
    "SimulationClock", "EventBus", "ScheduledTask", "Scheduler",
    "TelemetryRecorder", "Evaluator", "CheckpointManager",
    "ExperimentRunner", "CommunicationNetwork", "Depot",
    "LogisticsSystem", "EnvironmentModel", "SensorSuite", "Contact",
    "Scenario", "ScenarioSpec", "TaskSpec", "EventSpec",
    "build_default_scenario", "build_default_scenario_spec",
]
