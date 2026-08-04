#!/usr/bin/env python3
"""Tests for the AI Scientist (Phase 4)."""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import unittest
from brain.science.scientist import Scientist
from brain.science.hypothesis_generator import ScientistHypothesisGenerator, ResearchHypothesis
from brain.science.novelty_detector import NoveltyDetector
from brain.science.experiment_designer import ExperimentDesigner, ExperimentDesign
from brain.science.publication_writer import PublicationWriter, Publication
from brain.science.peer_reviewer import PeerReviewer
from brain.science.citation_network import CitationNetwork


class TestHypothesisGenerator(unittest.TestCase):
    def setUp(self):
        self.gen = ScientistHypothesisGenerator()

    def test_generate(self):
        hypothesis = self.gen.generate("multi-agent reinforcement learning")
        self.assertIsInstance(hypothesis, ResearchHypothesis)
        self.assertTrue(hypothesis.hypothesis_id)
        self.assertTrue(hypothesis.title)

    def test_get_stats(self):
        self.gen.generate("test")
        stats = self.gen.get_stats()
        self.assertIn("hypotheses_generated", stats)


class TestNoveltyDetector(unittest.TestCase):
    def setUp(self):
        self.detector = NoveltyDetector()

    def test_assess(self):
        report = self.detector.assess("test idea", keywords=["ai", "test"], related_work=["x"])
        self.assertIn("novelty_score", report)
        self.assertIn("verdict", report)

    def test_get_stats(self):
        self.detector.assess("test", related_work=["x"])
        stats = self.detector.get_stats()
        self.assertIn("assessments_performed", stats)


class TestExperimentDesigner(unittest.TestCase):
    def setUp(self):
        self.designer = ExperimentDesigner()

    def test_design(self):
        design = self.designer.design("H-1", "Test design")
        self.assertIsInstance(design, ExperimentDesign)
        self.assertEqual(design.hypothesis_id, "H-1")

    def test_get_stats(self):
        self.designer.design("H-1", "Test")
        stats = self.designer.get_stats()
        self.assertIn("designs_created", stats)


class TestPublicationWriter(unittest.TestCase):
    def setUp(self):
        self.writer = PublicationWriter()

    def test_draft(self):
        pub = self.writer.draft("Test Paper", "Abstract", results={"acc": 0.9})
        self.assertIsInstance(pub, Publication)
        self.assertIn("introduction", pub.sections)

    def test_get_stats(self):
        self.writer.draft("T", "A")
        stats = self.writer.get_stats()
        self.assertIn("publications_drafted", stats)


class TestPeerReviewer(unittest.TestCase):
    def setUp(self):
        self.reviewer = PeerReviewer()

    def test_review(self):
        from brain.science.publication_writer import Publication
        pub = Publication(title="Test", abstract="novel approach",
                          sections={"introduction": "A novel approach", "methods": "M", "results": "R"})
        review = self.reviewer.review(pub)
        self.assertIn("overall_score", review)
        self.assertIn("recommendation", review)

    def test_get_stats(self):
        self.reviewer.review(Publication(title="T"))
        stats = self.reviewer.get_stats()
        self.assertIn("reviews_completed", stats)


class TestCitationNetwork(unittest.TestCase):
    def setUp(self):
        self.net = CitationNetwork()

    def test_citations(self):
        self.net.add_paper("A", "Paper A")
        self.net.add_paper("B", "Paper B")
        self.net.add_citation("B", "A")
        self.assertEqual(self.net.citation_count("A"), 1)
        self.assertEqual(self.net.get_cited_by("A"), ["B"])

    def test_get_stats(self):
        self.net.add_paper("A", "A")
        self.net.add_paper("B", "B")
        self.net.add_citation("B", "A")
        stats = self.net.get_stats()
        self.assertIn("papers", stats)


class TestScientist(unittest.TestCase):
    def setUp(self):
        self.scientist = Scientist()

    def test_run_research_cycle(self):
        session = self.scientist.run_research_cycle(
            "multi-agent coordination",
            keywords=["rl", "marl"],
            related_work=["madqn"],
        )
        self.assertIn("session_id", session)
        self.assertIn("hypothesis", session)
        self.assertIn("review", session)

    def test_get_stats(self):
        self.scientist.run_research_cycle("test")
        stats = self.scientist.get_stats()
        self.assertIn("research_cycles", stats)


if __name__ == "__main__":
    unittest.main(verbosity=2)
