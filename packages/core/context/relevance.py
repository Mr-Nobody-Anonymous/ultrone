# Copyright (c) Ultrone Contributors. All rights reserved.
"""Relevance ranking for memory, skills, and documentation chunks."""

from __future__ import annotations

import re
from typing import List, Tuple


class RelevanceRanker:
    """Ranks context chunks by keyword and semantic overlap with the active goal."""

    @staticmethod
    def rank_items(query: str, items: List[str], top_k: int = 5) -> List[str]:
        """Rank text items by relevance to query."""
        if not query or not items:
            return items[:top_k]

        query_tokens = set(re.findall(r"\w+", query.lower()))
        if not query_tokens:
            return items[:top_k]

        scored: List[Tuple[float, str]] = []
        for item in items:
            item_tokens = set(re.findall(r"\w+", item.lower()))
            overlap = len(query_tokens & item_tokens)
            score = overlap / len(query_tokens)
            scored.append((score, item))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [item for _, item in scored[:top_k]]
