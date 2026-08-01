#!/usr/bin/env python3
"""Tests for World Modeling (Phase 11)."""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import unittest
from sim.world_modeling.base import WorldModel, WorldModelConfig
from sim.world_modeling.terrain import TerrainModel, TerrainConfig
from sim.world_modeling.weather import WeatherModel, WeatherConfig
from sim.world_modeling.resource import ResourceModel, ResourceConfig
from sim.world_modeling.logistics import LogisticsModel, LogisticsConfig
from sim.world_modeling.event_scheduler import EventScheduler, EventSchedulerConfig
from sim.world_modeling.sensor_uncertainty import SensorUncertaintyModel, SensorUncertaintyConfig
from sim.world_modeling.stochastic_events import StochasticEventGenerator, StochasticEventConfig


class TestWorldModelInterface(unittest.TestCase):
    def test_base_instantiation_fails(self):
        with self.assertRaises(TypeError):
            WorldModel(WorldModelConfig())

    def test_terrain_implements_interface(self):
        m = TerrainModel()
        self.assertIsInstance(m, WorldModel)

    def test_weather_implements_interface(self):
        m = WeatherModel()
        self.assertIsInstance(m, WorldModel)

    def test_resource_implements_interface(self):
        m = ResourceModel()
        self.assertIsInstance(m, WorldModel)

    def test_logistics_implements_interface(self):
        m = LogisticsModel()
        self.assertIsInstance(m, WorldModel)

    def test_event_scheduler_implements_interface(self):
        m = EventScheduler()
        self.assertIsInstance(m, WorldModel)

    def test_sensor_uncertainty_implements_interface(self):
        m = SensorUncertaintyModel()
        self.assertIsInstance(m, WorldModel)

    def test_stochastic_events_implements_interface(self):
        m = StochasticEventGenerator()
        self.assertIsInstance(m, WorldModel)


class TestTerrainModel(unittest.TestCase):
    def setUp(self):
        self.model = TerrainModel()

    def test_update(self):
        self.model.update(dt=0.1)
        state = self.model.get_state()
        self.assertIn("type", state)

    def test_get_stats(self):
        stats = self.model.get_stats()
        self.assertIn("num_cells", stats)


class TestWeatherModel(unittest.TestCase):
    def setUp(self):
        self.model = WeatherModel()

    def test_update_and_state(self):
        self.model.update(dt=1.0)
        state = self.model.get_state()
        self.assertIn("condition", state)


class TestResourceModel(unittest.TestCase):
    def setUp(self):
        self.model = ResourceModel()

    def test_update(self):
        self.model.update(dt=1.0)
        state = self.model.get_state()
        self.assertIsNotNone(state)


class TestEventScheduler(unittest.TestCase):
    def setUp(self):
        self.model = EventScheduler()

    def test_schedule_and_step(self):
        self.model.schedule_event("test_event", delay=5)
        self.model.update(dt=1.0)
        state = self.model.get_state()
        self.assertIn("pending_events", state)


class TestSensorUncertainty(unittest.TestCase):
    def setUp(self):
        self.model = SensorUncertaintyModel()

    def test_apply_noise(self):
        reading = {"position": (1.0, 2.0), "confidence": 0.9}
        noisy = self.model.apply_noise(reading)
        self.assertIsNotNone(noisy)


class TestStochasticEvents(unittest.TestCase):
    def setUp(self):
        self.model = StochasticEventGenerator()

    def test_generate(self):
        event = self.model.generate()
        self.assertIsNotNone(event)


if __name__ == "__main__":
    unittest.main(verbosity=2)

