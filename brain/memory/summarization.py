# Copyright (c) Ultrone Contributors. All rights reserved.
"""Memory Summarizer — produces extractive summaries of memory groups.

Uses extractive summarization (frequency-based sentence selection) so that
memory is distilled without requiring an external LLM.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from .base import MemoryItem

logger = logging.getLogger("Ultrone.Brain.Memory.Summarization")


@dataclass
class SummarizationConfig:
    """Configuration for memory summarization."""
    max_sentences: int = 3
    min_word_freq: int = 1


class MemorySummarizer:
    """Creates extractive summaries of memory items."""

    def __init__(self, config: Optional[SummarizationConfig] = None):
        self.config = config or SummarizationConfig()
        self._summaries: int = 0

    def summarize(self, items: List[MemoryItem]) -> str:
        """Summarize a list of memory items into a short extractive summary."""
        texts = [self._extract_text(it.content) for it in items]
        texts = [t for t in texts if t]
        if not texts:
            return ""
        combined = " ".join(texts)
        summary = self._extractive_summary(combined)
        self._summaries += 1
        return summary

    def _extract_text(self, content: Any) -> str:
        if isinstance(content, str):
            return content
        if isinstance(content, dict):
            return " ".join(str(v) for v in content.values())
        if isinstance(content, (list, tuple)):
            return " ".join(str(x) for x in content)
        return str(content)

    def _extractive_summary(self, text: str) -> str:
        """Select the most frequent-keyword sentences."""
        sentences = re.split(r"(?<=[.!?])\s+", text.strip())
        if len(sentences) <= self.config.max_sentences:
            return " ".join(sentences)

        # Word frequency scoring
        words = re.findall(r"\w+", text.lower())
        freq: Dict[str, int] = {}
        for w in words:
            if len(w) > 2:
                freq[w] = freq.get(w, 0) + 1

        scored = []
        for sent in sentences:
            score = sum(freq.get(w, 0) for w in re.findall(r"\w+", sent.lower()))
            scored.append((score, sent))

        scored.sort(key=lambda x: x[0], reverse=True)
        top = [s for _, s in scored[: self.config.max_sentences]]
        # Preserve original order
        ordered = [s for s in sentences if s in top]
        return " ".join(ordered)

    def get_stats(self) -> Dict[str, Any]:
        return {
            "type": "MemorySummarizer",
            "summaries_generated": self._summaries,
        }
