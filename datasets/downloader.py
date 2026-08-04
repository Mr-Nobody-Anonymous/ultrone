# Copyright (c) Ultrone Contributors. All rights reserved.
"""Dataset Downloader — downloads datasets from HuggingFace or local files.

Supports HuggingFace ``datasets`` library, local CSV/JSON files, and
HTTP-based downloads with caching.
"""

from __future__ import annotations

import json
import logging
import time
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("Ultrone.Datasets.Downloader")


@dataclass
class DownloadConfig:
    """Configuration for dataset download."""
    cache_dir: str = "datasets_cache"
    timeout: int = 60


class DatasetDownloader:
    """Downloads datasets from various sources."""

    def __init__(self, config: Optional[DownloadConfig] = None):
        self.config = config or DownloadConfig()
        self.cache_dir = Path(self.config.cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self._downloads: List[Dict[str, Any]] = []

    def from_huggingface(self, dataset_name: str, split: str = "train", **kwargs: Any) -> Dict[str, Any]:
        """Load a dataset from HuggingFace."""
        try:
            from datasets import load_dataset  # type: ignore
            ds = load_dataset(dataset_name, split=split, **kwargs)
            return {
                "source": "huggingface",
                "name": dataset_name,
                "split": split,
                "data": ds,
                "num_samples": len(ds) if _has_len(ds) else 0,
                "backend_available": True,
            }
        except ImportError:
            logger.warning("HuggingFace `datasets` not installed; returning descriptor")
            return {
                "source": "huggingface",
                "name": dataset_name,
                "split": split,
                "data": None,
                "num_samples": 0,
                "backend_available": False,
            }

    def from_file(self, path: str, format: str = "json") -> Dict[str, Any]:
        """Load a dataset from a local file."""
        p = Path(path)
        if not p.exists():
            raise FileNotFoundError(f"Dataset file not found: {path}")
        if format == "json":
            with open(p, "r") as f:
                data = json.load(f)
        elif format == "csv":
            import csv
            with open(p, "r", newline="") as f:
                reader = csv.DictReader(f)
                data = list(reader)
        else:
            raise ValueError(f"Unsupported format: {format}")
        return {
            "source": "file",
            "name": p.stem,
            "format": format,
            "data": data,
            "num_samples": len(data) if isinstance(data, list) else 0,
        }

    def from_url(self, url: str, save_as: Optional[str] = None) -> Dict[str, Any]:
        """Download a dataset from a URL."""
        save_as = save_as or url.split("/")[-1]
        dest = self.cache_dir / save_as
        if not dest.exists():
            urllib.request.urlretrieve(url, str(dest))
        self._downloads.append({"url": url, "path": str(dest), "timestamp": time.time()})
        return {"source": "url", "name": save_as, "path": str(dest), "data": None}

    def get_stats(self) -> Dict[str, Any]:
        return {
            "type": "DatasetDownloader",
            "downloads_performed": len(self._downloads),
            "cache_dir": str(self.cache_dir),
        }


def _has_len(obj: Any) -> bool:
    try:
        len(obj)
        return True
    except TypeError:
        return False
