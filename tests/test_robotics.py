#!/usr/bin/env python3
"""Tests for the Robotics package."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
import unittest
import numpy as np
from robotics.robot_interface import RobotInterface, RobotState
from robotics.controller import RobotController

class TestRobotInterface(unittest.TestCase):
    def test_connect_disconnect(self):
        robot = RobotInterface()
        self.assertTrue(robot.connect())
        self.assertTrue(robot.is_connected)
        robot.disconnect()
        self.assertFalse(robot.is_connected)
    def test_get_state(self):
        robot = RobotInterface()
        state = robot.get_state()
        self.assertIsInstance(state, RobotState)

class TestRobotController(unittest.TestCase):
    def test_plan_path(self):
        controller = RobotController()
        path = controller.plan_path(np.zeros(3), np.array([10.0, 0.0, 0.0]))
        self.assertEqual(controller.trajectory_length, 11)
        self.assertGreater(path[-1][0], path[0][0])

if __name__ == "__main__":
    unittest.main(verbosity=2)
