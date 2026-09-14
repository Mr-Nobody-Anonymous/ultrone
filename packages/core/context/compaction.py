# Copyright (c) Ultrone Contributors. All rights reserved.
"""Context Compaction and Truncation strategies."""

from __future__ import annotations

from typing import List

from .token_counter import TokenCounter


class ContextCompactor:
    """Compacts text blocks to fit within maximum token allowances."""

    @staticmethod
    def compact_text(text: str, max_tokens: int) -> str:
        """Truncate or summarize text to strictly fit within max_tokens."""
        current_tokens = TokenCounter.count_tokens(text)
        if current_tokens <= max_tokens:
            return text

        lines = text.splitlines()
        if len(lines) <= 2:
            chars_allowed = max_tokens * 3
            return text[:chars_allowed] + "\n...[truncated]"

        # Preserve head and tail of document
        keep_lines: List[str] = []
        head_count = len(lines) // 3
        tail_count = len(lines) // 3

        head = lines[:head_count]
        tail = lines[-tail_count:]
        summary_marker = f"\n... [compacted {len(lines) - head_count - tail_count} lines] ...\n"

        compacted = "\n".join(head) + summary_marker + "\n".join(tail)
        if TokenCounter.count_tokens(compacted) > max_tokens:
            chars_allowed = max_tokens * 3
            return compacted[:chars_allowed] + "\n...[truncated]"

        return compacted
