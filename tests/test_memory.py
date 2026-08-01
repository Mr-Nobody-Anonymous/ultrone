#!/usr/bin/env python3
"""Tests for Memory Systems (Phase 10)."""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import unittest
import numpy as np
from brain.memory.base import BaseMemory, MemoryConfig, MemoryItem
from brain.memory.episodic_memory import EpisodicMemory, EpisodicConfig
from brain.memory.semantic_memory import SemanticMemory, SemanticConfig
from brain.memory.working_memory import WorkingMemory, WorkingMemoryConfig
from brain.memory.associative_memory import AssociativeMemory, AssociativeConfig
from brain.memory.memory_consolidation import MemoryConsolidation, ConsolidationConfig


class TestMemoryInterface(unittest.TestCase):
    def test_base_instantiation_fails(self):
        with self.assertRaises(TypeError):
            BaseMemory(MemoryConfig())

    def test_episodic_implements_interface(self):
        m = EpisodicMemory()
        self.assertIsInstance(m, BaseMemory)

    def test_semantic_implements_interface(self):
        m = SemanticMemory()
        self.assertIsInstance(m, BaseMemory)

    def test_working_implements_interface(self):
        m = WorkingMemory()
        self.assertIsInstance(m, BaseMemory)

    def test_associative_implements_interface(self):
        m = AssociativeMemory()
        self.assertIsInstance(m, BaseMemory)


class TestEpisodicMemory(unittest.TestCase):
    def setUp(self):
        self.memory = EpisodicMemory()

    def test_store_and_recall(self):
        self.memory.store("event_1", {"position": (1, 2)})
        recalled = self.memory.recall("event_1")
        self.assertIsNotNone(recalled)

    def test_get_stats(self):
        stats = self.memory.get_stats()
        self.assertIn("num_episodes", stats)


class TestSemanticMemory(unittest.TestCase):
    def setUp(self):
        self.memory = SemanticMemory()

    def test_store_and_query(self):
        self.memory.store("concept_1", {"is_ally": True})
        result = self.memory.query("concept_1")
        self.assertIsNotNone(result)


class TestWorkingMemory(unittest.TestCase):
    def setUp(self):
        self.memory = WorkingMemory()

    def test_hold_and_recall(self):
        self.memory.hold("temp_data", 42.0)
        val = self.memory.recall("temp_data")
        self.assertEqual(val, 42.0)

    def test_decay(self):
        self.memory.hold("temp", 1.0)
        self.memory.decay()
        val = self.memory.recall("temp")
        self.assertIsNotNone(val)

    def test_get_stats(self):
        stats = self.memory.get_stats()
        self.assertIn("capacity", stats)


class TestAssociativeMemory(unittest.TestCase):
    def setUp(self):
        self.memory = AssociativeMemory()

    def test_associate(self):
        self.memory.associate("trigger_A", "response_B")
        result = self.memory.recall("trigger_A")
        self.assertIn("response_B", result)


class TestMemoryConsolidation(unittest.TestCase):
    def setUp(self):
        self.episodic = EpisodicMemory()
        self.semantic = SemanticMemory()
        self.consolidation = MemoryConsolidation(
            source=self.episodic,
            target=self.semantic,
        )

    def test_consolidate(self):
        self.episodic.store("test_event", {"data": 1})
        self.consolidation.consolidate()
        stats = self.consolidation.get_stats()
        self.assertIn("num_consolidations", stats)


if __name__ == "__main__":
    unittest.main(verbosity=2)

