# Copyright (c) Ultrone Contributors. All rights reserved.
"""Token counter utility for context estimation."""

from __future__ import annotations


class TokenCounter:
    """Estimates and counts token consumption for text payloads."""

    @staticmethod
    def count_tokens(text: str) -> int:
        """Estimate token count (roughly 4 characters or ~0.75 words per token)."""
        if not text:
            return 0
        # Fast heuristic: max(len(text)//4, int(len(text.split()) * 1.3))
        words = len(text.split())
        chars = len(text)
        return max(1, max(chars // 4, int(words * 1.3)))
