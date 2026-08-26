# ULTRONE Agents Architecture

## Overview

The `agents/` package provides a production-quality, research-grade, modular agent framework for the ULTRONE simulation environment. It implements a complete multi-domain agent architecture supporting air, land, sea, space, and cyber domains.

## Architecture

```
BaseAgent (abstract base)
  └── SubsystemControlledAgent (CommandBus + composed subsystems)
        ├── AirAgent
        │   ├── DroneAgent            # propulsion/flight_control/nav/sensors/
        │   ├── FighterAgent          # comms/power/payload/health/environment/
        │   └── MissileAgent          # autonomy
        ├── LandAgent
        │   ├── TankAgent             # propulsion/mobility/nav/sensors/comms/
        │   ├── InfantryAgent         # power/health/autonomy
        │   └── MobileMissileAgent
        ├── SeaAgent
        │   ├── VesselAgent           # + BallastSubsystem & SonarSubsystem
        │   ├── SubmarineAgent        #   on submarines
        │   └── NavalAirAgent
        ├── SpaceAgent                # power/thermal/attitude/orbital_navigation/
        │   ├── SatelliteAgent        # nav/sensors/comms/payload/health/autonomy
        │   ├── OrbitalAgent
        │   └── SpaceWeaponAgent
        ├── CyberAgent                # compute/storage/network/services/auth/
        │   ├── ReconAgent            # monitoring/configuration/defensive_controls
        │   ├── ExploitAgent
        │   └── DefendAgent
        ├── RoboticPlatformAgent      # GENERAL domain (simulation-only)
        │   ├── GroundRobotAgent / AerialRobotAgent /
        │   └── UnderwaterRobotAgent / IndustrialRobotAgent
        └── InfrastructureNodeAgent   # GENERAL domain (simulation-only)
            ├── PowerGridAgent / CommsInfrastructureAgent /
            └── IndustrialPlantAgent / TransitNetworkAgent
```

## Subsystem-Level Control

Every platform is a composition of subsystem objects behind a structured
command bus (`agents.commands`). Higher-level AI operates machines through
one uniform interface regardless of platform kind:

```python
from agents.commands import Command

agent.execute(Command("propulsion", "set_throttle", {"value": 0.65}))
agent.execute(Command("navigation", "set_destination",
                      {"position": [10.0, 5.0]}))

agent.available_capabilities()     # pruned hierarchical capability tree
agent.platform_state.get()         # unified snapshot across all subsystems
agent.tick_platform(tick)          # deterministic dynamics step
agent.telemetry_recorder.export()  # command log + snapshot history
```

Key modules:
- `agents/platform_agent.py` -- SubsystemControlledAgent base + per-domain default compositions
- `agents/state.py` -- PlatformStateView read model over the bus
- `agents/telemetry.py` -- bounded telemetry recorder
- `agents/subsystems/` -- the subsystem library, one concern per module:
  core set in `propulsion`-shaped `platform_subsystems.py`; canonical
  homes for `thermal.py`, `attitude.py`, `environment.py`,
  `resource.py`, `locomotion.py` (+ legacy re-export shims); domain
  extensions in `flight.py`, `naval.py` (ballast/sonar), `orbital.py`;
  computing-node surfaces in `computing.py`; and the cross-cutting
  primitives `life_support.py`, `diagnostics.py`, `safety.py`
- `agents/platform_control.py` -- unified PlatformState builder
  (`get_platform_state(agent | controller | bus)`) and the UCL bridge

### One command path

For bus-driven platforms there is exactly ONE actuation mechanism::

    UCL verb -> structured Command -> CommandBus -> subsystems -> state

`sandbox.ucl.PlatformController.execute_command` / `manage_system` /
`move` / `communicate` all terminate in the same CommandBus (`manage_system`
accepts a structured Command or its `{subsystem, action, parameters}`
dict form; adapter fallback exists only for legacy bus-less machines).
Safety enforcement lives IN the bus: an engaged
`SafetyInterlockSubsystem` ("safety") blocks every non-safety command
from every caller until released -- one gate because one path.
Fault injection (`agents.subsystems.faults.FaultInjector`) covers engine
failure, sensor blindness, communication blackout, power depletion,
navigation failure, overheating, degradation, fuel leaks, conflicting
and invalid commands -- all surfaced through the unified state's
`active_faults`.

Simulation boundary: the command system models detailed operation of
sandboxed simulated platforms only. There is intentionally no interface --
and no path -- toward operating real-world weapons, vehicles,
infrastructure, or computer systems.

## Agent Lifecycle

Agents follow a deterministic lifecycle:

```
INITIALIZED → READY → ACTIVE ↔ PAUSED → DEGRADED → INACTIVE
```

The lifecycle is managed via `AgentStatus` enum in `agents.config`.

## Configuration

All configurable parameters use dataclasses with validation:

- `AgentConfig` - Base configuration for all agents
- `AirAgentConfig` - Air domain specific (altitude, speed, fuel, stealth)
- `LandAgentConfig` - Land domain specific (terrain, armor, weapons)
- `SeaAgentConfig` - Sea domain specific (depth, sonar, displacement)
- `SpaceAgentConfig` - Space domain specific (orbit, delta-v, power)
- `CyberAgentConfig` - Cyber domain specific (nodes, bandwidth, encryption)

Configuration supports:
- Deterministic simulation
- Reproducible experiments
- Serialization
- Validation with sensible defaults

## Capabilities

Agents expose capabilities through structured interfaces:

```python
from agents.base_agent import AgentCapability

agent.can_perform(AgentCapability.SENSE)
agent.can_perform(AgentCapability.MOVE)
agent.can_perform(AgentCapability.ENGAGE)
agent.can_perform(AgentCapability.COMMUNICATE)
```

## Integration Points

### Communication

Agents integrate with `comms.message_bus.MessageBus`:

```python
agent = BaseAgent(..., message_bus=message_bus)
```

Agents publish state changes, damage events, and contact reports to the message bus.

### Serialization

All agents support serialization:

```python
data = agent.to_dict()      # Serialize
agent.from_dict(data)       # Deserialize
```

### Domain-Specific Behaviors

Each domain base class provides:

**AirAgent**: altitude management, fuel consumption, sensor range at altitude  
**LandAgent**: terrain compatibility, movement, armor, weapon range  
**SeaAgent**: depth management, stealth mode, sonar/radar state  
**SpaceAgent**: orbital state, delta-v, power management, communication delay  
**CyberAgent**: network operations, stealth, exploit/defense mechanics

## Registry and Factory

### Registry

```python
from agents.registry import AgentRegistry, _default_registry

# List all agent types
types = _default_registry.list_agent_types()

# List agents by domain
air_agents = _default_registry.list_agent_types(DomainType.AIR)

# Get agent class
agent_cls = _default_registry.get_agent_class("drone")
```

### Factory

```python
from agents.registry import create_agent

# Create an agent by type
agent = create_agent(
    agent_type="drone",
    unit_id="drone-1",
    position=(0.0, 0.0, 5000.0),
    team="blue",
)
```

### Domain-Specific Factories

```python
from agents.air.factory import create_drone, create_fighter, create_missile
from agents.land.factory import create_tank, create_infantry, create_mobile_missile
from agents.sea.factory import create_vessel, create_submarine, create_naval_air
from agents.space.factory import create_satellite, create_orbital, create_space_weapon
from agents.cyber.factory import create_recon, create_exploit, create_defense
```

## File Structure

```
agents/
├── __init__.py          # Package init, auto-registers all agents
├── base_agent.py        # Abstract base agent class
├── config.py            # Configuration dataclasses
├── registry.py          # Agent registry and factory
│
├── air/
│   ├── __init__.py
│   ├── base.py          # AirAgent base class
│   ├── drone.py         # Compatibility wrapper
│   ├── drone_agent.py   # DroneAgent implementation
│   ├── fighter.py       # Compatibility wrapper
│   ├── fighter_agent.py # FighterAgent implementation
│   ├── missile.py       # Compatibility wrapper
│   ├── missile_agent.py # MissileAgent implementation
│   └── factory.py       # Air domain factory
│
├── land/
│   ├── __init__.py
│   ├── base.py          # LandAgent base class
│   ├── tank.py          # Compatibility wrapper
│   ├── tank_agent.py    # TankAgent implementation
│   ├── infantry.py      # Compatibility wrapper
│   ├── infantry_agent.py # InfantryAgent implementation
│   ├── mobile_missile.py # Compatibility wrapper
│   ├── mobile_missile_agent.py # MobileMissileAgent implementation
│   └── factory.py       # Land domain factory
│
├── sea/
│   ├── __init__.py
│   ├── base.py          # SeaAgent base class
│   ├── vessel.py        # Compatibility wrapper
│   ├── vessel_agent.py  # VesselAgent implementation
│   ├── submarine.py     # Compatibility wrapper
│   ├── submarine_agent.py # SubmarineAgent implementation
│   ├── naval_air.py     # Compatibility wrapper
│   ├── naval_air_agent.py # NavalAirAgent implementation
│   └── factory.py       # Sea domain factory
│
├── space/
│   ├── __init__.py
│   ├── base.py          # SpaceAgent base class
│   ├── satellite.py     # Compatibility wrapper
│   ├── satellite_agent.py # SatelliteAgent implementation
│   ├── orbital.py       # Compatibility wrapper
│   ├── orbital_agent.py # OrbitalAgent implementation
│   ├── space_weapon.py  # Compatibility wrapper
│   ├── space_weapon_agent.py # SpaceWeaponAgent implementation
│   └── factory.py       # Space domain factory
│
└── cyber/
    ├── __init__.py
    ├── base.py          # CyberAgent base class
    ├── reconnaissance.py # Compatibility wrapper
    ├── recon_agent.py   # ReconAgent implementation
    ├── exploit.py       # Compatibility wrapper
    ├── exploit_agent.py # ExploitAgent implementation
    ├── defense.py       # Compatibility wrapper
    ├── defend_agent.py  # DefendAgent implementation
    └── factory.py       # Cyber domain factory
```

## Extending Agents

### Creating a New Domain Agent

1. Create a domain base class inheriting from `BaseAgent`:
```python
from agents.base_agent import BaseAgent, AgentCapability
from agents.config import YourDomainConfig
from data.entities import DomainType

class YourDomainAgent(BaseAgent):
    def __init__(self, unit_id, position, team="blue", config=None, **kwargs):
        super().__init__(
            unit_id=unit_id,
            domain=DomainType.YOUR_DOMAIN,
            unit_type=self._get_unit_type(),
            position=position,
            team=team,
            capabilities=self._get_capabilities(),
            **kwargs,
        )
        self.config = config or YourDomainConfig(...)
```

2. Implement required abstract methods:
```python
    @abstractmethod
    def take_turn(self, world_state, messages):
        pass

    @abstractmethod
    def execute_mission(self, mission):
        pass
```

3. Register in factory:
```python
def register_your_domain_agents(registry=None):
    registry.register(
        agent_type="your_type",
        agent_class=YourAgent,
        domain=DomainType.YOUR_DOMAIN,
        description="...",
        config_class=YourDomainConfig,
    )
```

## Testing

Run agent tests:

```bash
python -m pytest tests/test_agents.py -v
```

Run all tests:

```bash
python -m pytest tests/ -k agent -v
```

## Reproducibility

All agents are deterministic when initialized with the same parameters. No uncontrolled global random state is used.

## Integration with ULTRONE Systems

The agents package integrates with:
- `data.entities` - Unit, Contact, DomainType, AgentState
- `comms.protocol` - Message, MessageType, Priority
- `comms.message_bus` - Async pub/sub communication
- `brain.perception` - Observation processing
- `brain.memory` - Memory systems
- `brain.reasoning` - Planners and decision policies
- `sim` - Simulation environment

## Research-Grade Features

- Modular design for ablation studies
- Serializable for experiment checkpoints
- Cloneable for Monte Carlo and evolutionary algorithms
- Compatible with RL environments
- Supports multi-agent coordination protocols
- Deterministic execution for reproducibility