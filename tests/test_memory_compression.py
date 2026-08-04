#!/usr/bin/env python3
"""Tests for Memory Compression (Phase 2)."""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import unittest
import time

from brain.memory.base import MemoryItem
from brain.memory.importance import ImportanceScorer, ImportanceConfig
from brain.memory.forgetting import ForgettingEngine, ForgettingConfig
from brain.memory.compression import MemoryCompressor, CompressionConfig
from brain.memory.summarization import MemorySummarizer, SummarizationConfig
from brain.memory.memory_index import MemoryIndex, IndexConfig
from brain.memory.retrieval_optimizer import RetrievalOptimizer, RetrievalConfig


class TestImportanceScorer(unittest.TestCase):
    def setUp(self):
        self.scorer = ImportanceScorer()

    def test_score(self):
        item = MemoryItem(key="k1", content="data", timestamp=time.time(), importance=0.8)
        score = self.scorer.score(item)
        self.assertGreaterEqual(score, 0.0)
        self.assertLessEqual(score, 1.0)

    def test_rank(self):
        items = [
            MemoryItem(key="a", content="x", timestamp=time.time(), importance=0.1),
            MemoryItem(key="b", content="y", timestamp=time.time(), importance=0.9),
        ]
        ranked = self.scorer.rank(items)
        self.assertEqual(ranked[0].key, "b")


class TestForgettingEngine(unittest.TestCase):
    def test_evict_lru(self):
        engine = ForgettingEngine(ForgettingConfig(policy="lru", capacity=2))
        items = [
            MemoryItem(key="a", content=1, timestamp=1.0),
            MemoryItem(key="b", content=2, timestamp=2.0),
            MemoryItem(key="c", content=3, timestamp=3.0),
        ]
        evicted = engine.evict(items)
        self.assertEqual(len(evicted), 1)
        self.assertEqual(len(items), 2)
        self.assertEqual(evicted[0].key, "a")

    def test_evict_importance(self):
        engine = ForgettingEngine(ForgettingConfig(policy="importance", capacity=2))
        items = [
            MemoryItem(key="a", content=1, importance=0.1),
            MemoryItem(key="b", content=2, importance=0.5),
            MemoryItem(key="c", content=3, importance=0.9),
        ]
        engine.evict(items)
        self.assertEqual(len(items), 2)
        self.assertNotIn("a", [it.key for it in items])


class TestMemoryCompressor(unittest.TestCase):
    def test_truncate(self):
        comp = MemoryCompressor(CompressionConfig(method="truncate", max_tokens=5))
        item = MemoryItem(key="k", content="one two three four five six seven eight")
        result = comp.compress(item)
        self.assertEqual(len(result.content.split()), 5)

    def test_downsamples(self):
        comp = MemoryCompressor(CompressionConfig(method="downsampling"))
        item = MemoryItem(key="k", content=[1.0, 2.0, 3.0, 4.0])
        result = comp.compress(item)
        self.assertLess(len(result.content), 4)


class TestMemorySummarizer(unittest.TestCase):
    def test_summarize(self):
        summ = MemorySummarizer(SummarizationConfig(max_sentences=2))
        items = [
            MemoryItem(key="a", content="The battle was intense. Many units engaged."),
            MemoryItem(key="b", content="We held the position. Victory was achieved."),
        ]
        summary = summ.summarize(items)
        self.assertIsInstance(summary, str)
        self.assertGreater(len(summary), 0)


class TestMemoryIndex(unittest.TestCase):
    def test_add_and_search(self):
        idx = MemoryIndex()
        idx.add(MemoryItem(key="a", content="tank formation detected"))
        idx.add(MemoryItem(key="b", content="aircraft approaching"))
        results = idx.search("tank")
        self.assertIn("a", results)
        self.assertNotIn("b", results)


class TestRetrievalOptimizer(unittest.TestCase):
    def test_retrieve(self):
        opt = RetrievalOptimizer()
        items = [
            MemoryItem(key="a", content="ambush threat detected"),
            MemoryItem(key="b", content="supply route clear"),
        ]
        for it in items:
            opt.index_item(it)
        results = opt.retrieve(items, "ambush")
        self.assertEqual(results[0].key, "a")

    def test_cache(self):
        opt = RetrievalOptimizer()
        items = [MemoryItem(key="a", content="hello world")]
        for it in items:
            opt.index_item(it)
        opt.retrieve(items, "hello")
        opt.retrieve(items, "hello")
        self.assertIn("hello", opt._cache)


if __name__ == "__main__":
    unittest.main(verbosity=2)

