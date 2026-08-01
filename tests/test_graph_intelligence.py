#!/usr/bin/env python3
"""Tests for Graph Intelligence modules (Phase 7)."""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import unittest
import numpy as np
from brain.perception.graph_intelligence.gnn import GraphNeuralNetwork, GNNConfig
from brain.perception.graph_intelligence.gat import GraphAttentionNetwork, GATConfig
from brain.perception.graph_intelligence.knowledge_embeddings import KnowledgeEmbeddings, KGEConfig
from brain.perception.graph_intelligence.community_detection import CommunityDetection, CommunityConfig
from brain.perception.graph_intelligence.temporal_graph import TemporalGraph, TemporalGraphConfig


class TestGNN(unittest.TestCase):
    def setUp(self):
        self.gnn = GraphNeuralNetwork()

    def test_forward(self):
        x = np.random.randn(5, 8)
        adj = np.eye(5)
        out = self.gnn.forward(x, adj)
        self.assertIsNotNone(out)

    def test_get_stats(self):
        stats = self.gnn.get_stats()
        self.assertIn("type", stats)


class TestGAT(unittest.TestCase):
    def setUp(self):
        self.gat = GraphAttentionNetwork()

    def test_forward(self):
        x = np.random.randn(5, 8)
        adj = np.eye(5)
        out = self.gat.forward(x, adj)
        self.assertIsNotNone(out)


class TestKnowledgeEmbeddings(unittest.TestCase):
    def setUp(self):
        self.ke = KnowledgeEmbeddings()

    def test_embed(self):
        result = self.ke.embed(["entity_1", "entity_2"])
        self.assertIsNotNone(result)

    def test_get_stats(self):
        stats = self.ke.get_stats()
        self.assertIn("num_entities", stats)


class TestCommunityDetection(unittest.TestCase):
    def setUp(self):
        self.cd = CommunityDetection()

    def test_detect(self):
        adj = np.array([[0, 1, 1], [1, 0, 0], [1, 0, 0]])
        communities = self.cd.detect(adj)
        self.assertIsNotNone(communities)


class TestTemporalGraph(unittest.TestCase):
    def setUp(self):
        self.tg = TemporalGraph()

    def test_analyze(self):
        snapshots = [np.eye(3) for _ in range(5)]
        result = self.tg.analyze(snapshots)
        self.assertIsNotNone(result)


if __name__ == "__main__":
    unittest.main(verbosity=2)

