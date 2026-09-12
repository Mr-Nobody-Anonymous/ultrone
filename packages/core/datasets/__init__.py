# Copyright (c) Ultrone Contributors. All rights reserved.
"""Dataset Management — registry, downloader, preprocessing, augmentation,
validation, synthetic generation, versioning, and metadata.

Supports HuggingFace datasets, custom datasets, synthetic generation,
caching, validation, statistics, and deduplication.
"""

from .registry import DatasetRegistry, DatasetEntry
from .downloader import DatasetDownloader
from .preprocessing import Preprocessor
from .augmentation import Augmenter
from .validation import DatasetValidator
from .synthetic_generator import SyntheticGenerator
from .versioning import DatasetVersioner
from .metadata import DatasetMetadata

__all__ = [
    "DatasetRegistry",
    "DatasetEntry",
    "DatasetDownloader",
    "Preprocessor",
    "Augmenter",
    "DatasetValidator",
    "SyntheticGenerator",
    "DatasetVersioner",
    "DatasetMetadata",
]
