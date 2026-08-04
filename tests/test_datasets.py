#!/usr/bin/env python3
"""Tests for Dataset Management (Phase 3)."""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import unittest
from datasets.registry import DatasetRegistry, DatasetEntry
from datasets.downloader import DatasetDownloader
from datasets.preprocessing import Preprocessor
from datasets.augmentation import Augmenter
from datasets.validation import DatasetValidator
from datasets.synthetic_generator import SyntheticGenerator
from datasets.versioning import DatasetVersioner
from datasets.metadata import DatasetMetadata, MetadataStore


class TestDatasetRegistry(unittest.TestCase):
    def setUp(self):
        self.reg = DatasetRegistry()

    def test_register_and_get(self):
        entry = DatasetEntry(name="test_ds", source="custom", num_samples=10)
        self.reg.register(entry)
        self.assertEqual(self.reg.get(entry.dataset_id).name, "test_ds")

    def test_search(self):
        self.reg.register(DatasetEntry(name="mnist", source="huggingface", tags=["vision"]))
        results = self.reg.search("mnist")
        self.assertEqual(len(results), 1)

    def test_get_stats(self):
        self.reg.register(DatasetEntry(name="a", source="custom"))
        stats = self.reg.get_stats()
        self.assertIn("total_datasets", stats)


class TestDatasetDownloader(unittest.TestCase):
    def setUp(self):
        self.dl = DatasetDownloader()

    def test_from_file_json(self):
        import json, tempfile, os
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
            json.dump([{"a": 1}, {"a": 2}], f)
            fname = f.name
        try:
            result = self.dl.from_file(fname, format="json")
            self.assertEqual(result["num_samples"], 2)
        finally:
            os.unlink(fname)

    def test_get_stats(self):
        stats = self.dl.get_stats()
        self.assertIn("downloads_performed", stats)


class TestPreprocessor(unittest.TestCase):
    def setUp(self):
        self.pp = Preprocessor()

    def test_fit_transform(self):
        rows = [{"a": 1.0}, {"a": 3.0}, {"a": 5.0}]
        result = self.pp.fit_transform(rows)
        self.assertEqual(len(result), 3)
        self.assertAlmostEqual(result[0]["a"], 0.0)
        self.assertAlmostEqual(result[2]["a"], 1.0)

    def test_standardize(self):
        pp = Preprocessor()
        pp.config.standardize = True
        rows = [{"a": 1.0}, {"a": 3.0}, {"a": 5.0}]
        result = pp.fit_transform(rows)
        self.assertAlmostEqual(result[1]["a"], 0.0, places=5)


class TestAugmenter(unittest.TestCase):
    def setUp(self):
        self.aug = Augmenter()

    def test_augment(self):
        rows = [{"a": 1.0, "b": 2.0}]
        result = self.aug.augment(rows, factor=3)
        self.assertEqual(len(result), 3)


class TestDatasetValidator(unittest.TestCase):
    def setUp(self):
        self.val = DatasetValidator()

    def test_validate(self):
        rows = [{"a": 1}, {"a": 2}, {"a": 1}]
        report = self.val.validate(rows)
        self.assertIn("duplicates", report)
        self.assertEqual(report["duplicates"], 1)

    def test_deduplicate(self):
        rows = [{"a": 1}, {"a": 1}, {"a": 2}]
        unique = self.val.deduplicate(rows)
        self.assertEqual(len(unique), 2)


class TestSyntheticGenerator(unittest.TestCase):
    def setUp(self):
        self.gen = SyntheticGenerator()

    def test_generate(self):
        rows = self.gen.generate()
        self.assertEqual(len(rows), 100)
        self.assertIn("label", rows[0])

    def test_generate_classification(self):
        rows = self.gen.generate_classification(n_classes=2)
        self.assertEqual(len(rows), 100)


class TestDatasetVersioner(unittest.TestCase):
    def setUp(self):
        self.ver = DatasetVersioner()

    def test_bump(self):
        v1 = self.ver.bump("ds1", "initial", level="minor")
        v2 = self.ver.bump("ds1", "update", level="minor")
        self.assertEqual(v1.version, "1.1.0")
        self.assertEqual(v2.version, "1.2.0")

    def test_get_history(self):
        self.ver.bump("ds1", "v1")
        self.ver.bump("ds1", "v2")
        self.assertEqual(len(self.ver.get_history("ds1")), 2)


class TestDatasetMetadata(unittest.TestCase):
    def setUp(self):
        self.store = MetadataStore()

    def test_compute(self):
        rows = [{"a": 1, "b": "x"}, {"a": 2, "b": "y"}]
        md = DatasetMetadata.compute(rows, name="test")
        self.assertEqual(md.num_rows, 2)
        self.assertEqual(md.num_columns, 2)

    def test_store_get(self):
        md = DatasetMetadata.compute([{"a": 1}], name="t")
        self.store.store("ds1", md)
        self.assertEqual(self.store.get("ds1").num_rows, 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
