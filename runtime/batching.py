from __future__ import annotations

from typing import Any, Callable, Iterable, List, Sequence, TypeVar

T = TypeVar("T")
U = TypeVar("U")


def batch_inference(
    fn: Callable[[Any], U],
    inputs: Sequence[Any],
    batch_size: int = 1,
) -> List[U]:
    """Apply a function over a sequence with simple micro-batching."""
    if not inputs:
        return []
    batch_size = max(1, int(batch_size))
    results: List[U] = []
    for start in range(0, len(inputs), batch_size):
        batch = list(inputs[start : start + batch_size])
        if len(batch) == 1:
            results.append(fn(batch[0]))
            continue
        try:
            batched_output = fn(batch)
            if isinstance(batched_output, list):
                if len(batched_output) != len(batch):
                    results.extend(fn(item) for item in batch)
                else:
                    results.extend(batched_output)
            else:
                results.extend([batched_output] * len(batch))
        except TypeError:
            results.extend(fn(item) for item in batch)
    return results


def recommended_batch_size(
    *,
    available_memory: int = 0,
    fallback: int = 1,
    max_batch_size: int = 8,
) -> int:
    """Choose a conservative batch size based on available memory."""
    if available_memory <= 0:
        return max(1, min(max_batch_size, fallback))
    if available_memory < 2 * 1024 * 1024 * 1024:
        return max(1, min(2, max_batch_size))
    if available_memory < 8 * 1024 * 1024 * 1024:
        return max(1, min(4, max_batch_size))
    return max(1, min(max_batch_size, 8))
