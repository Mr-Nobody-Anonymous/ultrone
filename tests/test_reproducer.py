#!/usr/bin/env python3
"""Tests for Paper Reproducer (Phase 4)."""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import unittest
from research.reproducer import PaperReproducer, ReproducerConfig


class TestPaperReproducer(unittest.TestCase):
    def setUp(self):
        self.repro = PaperReproducer()

    def _make_paper(self):
        from research_db.schema import PaperRecord
        return PaperRecord(
            title="Test Paper",
            algorithms=["PPO", "SAC"],
            hyperparameters={"lr": 0.001, "batch_size": 64},
            benchmark_results={"accuracy": 0.9, "f1_score": 0.85},
        )

    def test_reproduce(self):
        paper = self._make_paper()
        report = self.repro.reproduce(paper)
        self.assertIn("reproduction_id", report)
        self.assertIn("reproducibility_score", report)
        self.assertIn("code_snippet", report)

    def test_get_stats(self):
        paper = self._make_paper()
        self.repro.reproduce(paper)
        stats = self.repro.get_stats()
        self.assertIn("reproductions_performed", stats)
        self.assertEqual(stats["reproductions_performed"], 1)

    def test_get_best_reproduction(self):
        paper = self._make_paper()
        self.repro.reproduce(paper)
        best = self.repro.get_best_reproduction()
        self.assertIsNotNone(best)
        self.assertEqual(best["title"], "Test Paper")


if __name__ == "__main__":
    unittest.main(verbosity=2)
    
    
