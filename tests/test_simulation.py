#!/usr/bin/env python3
"""Tests for the Simulation package."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
import unittest
import numpy as np
from simulation.digital_twin import DigitalTwin, TwinConfig
from simulation.physics import PhysicsEngine
from simulation.environment_generator import EnvironmentGenerator

class TestDigitalTwin(unittest.TestCase):
    def test_step(self):
        twin = DigitalTwin()
        state = twin.reset()
        self.assertEqual(twin.step_count, 0)
        state = twin.step({"action": "move"})
        self.assertEqual(twin.step_count, 1)

class TestPhysicsEngine(unittest.TestCase):
    def test_add_body_and_step(self):
        engine = PhysicsEngine()
        bid = engine.add_body(1.0, [0.0, 0.0, 10.0])
        self.assertEqual(engine.body_count, 1)
        engine.step()
        pos = engine.get_position(bid)
        self.assertLess(pos[2], 10.0)

class TestEnvironmentGenerator(unittest.TestCase):
    def test_generate_terrain(self):
        gen = EnvironmentGenerator(seed=42)
        terrain = gen.generate_terrain(10, 10)
        self.assertEqual(terrain.shape, (10, 10))
    def test_generate_entities(self):
        gen = EnvironmentGenerator(seed=42)
        entities = gen.generate_entities(5)
        self.assertEqual(len(entities), 5)

if __name__ == "__main__":
    unittest.main(verbosity=2)
