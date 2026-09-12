# Copyright (c) Ultrone Contributors. All rights reserved.
"""Memory Compressor — reduces memory footprint via lossy compression.

Provides token-based truncation, bag-of-words vectorization, and numeric
downsampling for memory content while preserving key semantics.
"""

from __future__ import annotations

import logging
import zlib
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from .base import MemoryItem

logger = logging.getLogger("Ultrone.Brain.Memory.Compression")


@dataclass
class CompressionConfig:
    """Configuration for memory compression."""
    method: str = "truncate"      # truncate, tokenize, zlib, downsampling
    max_tokens: int = 128
    max_sequence: int = 256


class MemoryCompressor:
    """Compresses memory content to save space."""

    METHODS = ("truncate", "tokenize", "zlib", "downsampling")

    def __init__(self, config: Optional[CompressionConfig] = None):
        self.config = config or CompressionConfig()
        self._compressed: int = 0

    def compress(self, item: MemoryItem) -> MemoryItem:
        """Return a compressed copy of a memory item."""
        content = item.content
        if self.config.method == "truncate":
            content = self._truncate(content)
        elif self.config.method == "tokenize":
            content = self._tokenize(content)
        elif self.config.method == "zlib":
            content = self._zlib(content)
        elif self.config.method == "downsampling":
            content = self._downsample(content)

        self._compressed += 1
        return MemoryItem(
            key=item.key,
            content=content,
            timestamp=item.timestamp,
            importance=item.importance,
            metadata={**item.metadata, "compressed": True, "method": self.config.method},
        )

    def _truncate(self, content: Any) -> Any:
        if isinstance(content, str):
            words = content.split()
            return " ".join(words[: self.config.max_tokens])
        if isinstance(content, (list, tuple)):
            return list(content[: self.config.max_sequence])
        return content

    def _tokenize(self, content: Any) -> Any:
        """Bag-of-words token counts for text."""
        if isinstance(content, str):
            counts: Dict[str, int] = {}
            for word in content.lower().split():
                counts[word] = counts.get(word, 0) + 1
            return counts
        return content

    def _zlib(self, content: Any) -> Any:
        """Compress a string via zlib (returns bytes)."""
        if isinstance(content, str):
            return zlib.compress(content.encode("utf-8"))
        return content

    def _downsample(self, content: Any) -> Any:
        """Average-downsample a numeric sequence."""
        if isinstance(content, (list, tuple)) and content and all(isinstance(x, (int, float)) for x in content):
            n = max(1, len(content) // 2)
            chunk = max(1, len(content) // n)
            return [sum(content[i:i + chunk]) / len(content[i:i + chunk])
                    for i in range(0, len(content), chunk)]
        return content

    def compress_many(self, items: List[MemoryItem]) -> List[MemoryItem]:
        """Compress a list of memory items."""
        return [self.compress(it) for it in items]

    def get_stats(self) -> Dict[str, Any]:
        return {
            "type": "MemoryCompressor",
            "method": self.config.method,
            "items_compressed": self._compressed,
        }
