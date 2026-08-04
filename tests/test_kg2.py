#!/usr/bin/env python3
"""Tests for Knowledge Graph 2.0 extensions."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
import unittest

class TestKGExtensions(unittest.TestCase):
    def test_knowledge_graph(self):
        from knowledge_engine.knowledge_graph import KnowledgeGraph
        kg = KnowledgeGraph()
        self.assertIsNotNone(kg)
    def test_scene_graph(self):
        from brain.perception.situational_awareness import SceneGraph
        sg = SceneGraph()
        self.assertEqual(sg.node_count(), 0)

if __name__ == "__main__":
    unittest.main(verbosity=2)
