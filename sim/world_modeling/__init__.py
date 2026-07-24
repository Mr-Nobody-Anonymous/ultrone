"""World Modeling module for richer simulation capabilities.

Provides environmental models that affect agent performance
and decision-making:

- ``TerrainModel``: Dynamic terrain with elevation, cover, trafficability
- ``WeatherModel``: Weather effects on sensors, mobility, weapons
- ``ResourceModel``: Resource distribution and depletion
- ``LogisticsModel``: Supply chain and logistics simulation
- ``EventScheduler``: Stochastic event scheduling
- ``SensorUncertaintyModel``: Sensor noise and degradation
- ``StochasticEventGenerator``: Random battlefield events
"""

from .terrain import TerrainModel, TerrainConfig
from .weather import WeatherModel, WeatherConfig
from .resource import ResourceModel, ResourceConfig
from .logistics import LogisticsModel, LogisticsConfig
from .event_scheduler import EventScheduler, EventSchedulerConfig
from .sensor_uncertainty import SensorUncertaintyModel, SensorUncertaintyConfig
from .stochastic_events import StochasticEventGenerator, StochasticEventConfig

__all__ = [
    "TerrainModel", "TerrainConfig",
    "WeatherModel", "WeatherConfig",
    "ResourceModel", "ResourceConfig",
    "LogisticsModel", "LogisticsConfig",
    "EventScheduler", "EventSchedulerConfig",
    "SensorUncertaintyModel", "SensorUncertaintyConfig",
    "StochasticEventGenerator", "StochasticEventConfig",
]

