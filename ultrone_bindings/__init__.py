# Copyright (c) Ultrone Contributors. All rights reserved.
"""ULTRONE C++/CUDA Bindings — Python interface to high-performance kernels.

This module provides a unified Python interface to the C++/CUDA performance
modules. If the compiled extensions are available, they are used for maximum
performance. If not, pure Python fallbacks are used so the platform remains
fully functional without compilation.

This follows the hybrid language policy: C++/CUDA for performance-critical
kernels, Python for everything else, with graceful degradation.
"""

from __future__ import annotations

import logging
import math
from typing import List, Optional, Tuple

logger = logging.getLogger("Ultrone.Bindings")

# Try to import C++ extensions
_cpp_available = False
_cuda_available = False

try:
    import ultrone_core
    _cpp_available = True
    logger.info("ULTRONE C++ core module loaded")
except ImportError:
    logger.info("C++ core module not available — using Python fallbacks")

try:
    import ultrone_cuda
    _cuda_available = True
    logger.info("ULTRONE CUDA module loaded")
except ImportError:
    if _cpp_available:
        logger.info("CUDA module not available — using CPU C++ kernels")

try:
    import ultrone_pathfind
    _pathfind_available = True
except ImportError:
    _pathfind_available = False

try:
    import ultrone_tensor
    _tensor_available = True
except ImportError:
    _tensor_available = False


def is_cpp_available() -> bool:
    """Check if C++ extensions are available."""
    return _cpp_available


def is_cuda_available() -> bool:
    """Check if CUDA extensions are available."""
    return _cuda_available


# === Performance Kernels ===

def dot_product(a: List[float], b: List[float]) -> float:
    """Fast vector dot product."""
    if _cpp_available:
        return ultrone_core.dot_product(a, b)
    # Python fallback
    if len(a) != len(b) or not a:
        return 0.0
    return sum(x * y for x, y in zip(a, b))


def cosine_similarity(a: List[float], b: List[float]) -> float:
    """Fast cosine similarity."""
    if _cpp_available:
        return ultrone_core.cosine_similarity(a, b)
    # Python fallback
    if len(a) != len(b) or not a:
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return dot / (norm_a * norm_b)


def softmax(input: List[float], temperature: float = 1.0) -> List[float]:
    """Parallel softmax computation."""
    if _cpp_available:
        return ultrone_core.softmax(input, temperature)
    # Python fallback
    if not input:
        return []
    max_val = max(input)
    exp_vals = [math.exp((v - max_val) / temperature) for v in input]
    total = sum(exp_vals)
    if total == 0.0:
        total = 1.0
    return [v / total for v in exp_vals]


def top_k_indices(scores: List[float], k: int) -> List[int]:
    """Parallel top-k selection."""
    if _cpp_available:
        return ultrone_core.top_k_indices(scores, k)
    # Python fallback
    indices = list(range(len(scores)))
    indices.sort(key=lambda i: scores[i], reverse=True)
    return indices[:k]


def argmax(input: List[float]) -> int:
    """Parallel argmax."""
    if _cpp_available:
        return ultrone_core.argmax(input)
    # Python fallback
    if not input:
        return -1
    return max(range(len(input)), key=lambda i: input[i])


def l2_normalize(input: List[float]) -> List[float]:
    """Fast L2 normalization."""
    if _cpp_available:
        return ultrone_core.l2_normalize(input)
    # Python fallback
    norm = math.sqrt(sum(v * v for v in input))
    if norm == 0.0:
        return list(input)
    return [v / norm for v in input]


def attention(
    queries: List[float],
    keys: List[float],
    values: List[float],
    seq_len: int,
    dim: int,
) -> List[float]:
    """Fast attention computation."""
    if _cpp_available:
        return ultrone_core.attention(queries, keys, values, seq_len, dim)
    # Python fallback
    result = [0.0] * (seq_len * dim)
    scale = 1.0 / math.sqrt(dim)
    for i in range(seq_len):
        scores = [0.0] * seq_len
        for j in range(seq_len):
            for k in range(dim):
                scores[j] += queries[i * dim + k] * keys[j * dim + k] * scale
        weights = softmax(scores)
        for k in range(dim):
            for j in range(seq_len):
                result[i * dim + k] += weights[j] * values[j * dim + k]
    return result


# === Tensor Operations ===

def tensor_add(a: List[float], b: List[float]) -> List[float]:
    """Element-wise tensor addition."""
    if _tensor_available:
        return ultrone_tensor.add(a, b)
    return [x + y for x, y in zip(a, b)]


def tensor_mul(a: List[float], b: List[float]) -> List[float]:
    """Element-wise tensor multiplication."""
    if _tensor_available:
        return ultrone_tensor.mul(a, b)
    return [x * y for x, y in zip(a, b)]


def relu(input: List[float]) -> List[float]:
    """ReLU activation."""
    if _tensor_available:
        return ultrone_tensor.relu(input)
    return [max(0.0, v) for v in input]


def gelu(input: List[float]) -> List[float]:
    """GELU activation."""
    if _tensor_available:
        return ultrone_tensor.gelu(input)
    c = math.sqrt(2.0 / math.pi)
    return [0.5 * x * (1.0 + math.tanh(c * (x + 0.044715 * x ** 3))) for x in input]


def layer_norm(input: List[float], dim: int, eps: float = 1e-5) -> List[float]:
    """Layer normalization."""
    if _tensor_available:
        return ultrone_tensor.layer_norm(input, dim, eps)
    # Python fallback
    seq_len = len(input) // dim
    result = [0.0] * len(input)
    for i in range(seq_len):
        slice_data = input[i * dim:(i + 1) * dim]
        mean = sum(slice_data) / dim
        variance = sum((x - mean) ** 2 for x in slice_data) / dim
        inv_std = 1.0 / math.sqrt(variance + eps)
        for j in range(dim):
            result[i * dim + j] = (input[i * dim + j] - mean) * inv_std
    return result


# === Pathfinding ===

def astar_pathfind(
    grid: List[List[float]],
    start: Tuple[int, int],
    goal: Tuple[int, int],
    allow_diagonal: bool = True,
) -> List[Tuple[int, int]]:
    """A* pathfinding on a 2D grid."""
    if _pathfind_available:
        return ultrone_pathfind.astar(
            grid, start[0], start[1], goal[0], goal[1], allow_diagonal
        )
    # Python fallback (simple BFS)
    from collections import deque
    if not grid:
        return []
    rows, cols = len(grid), len(grid[0])
    queue = deque([(start[0], start[1], [start])])
    visited = {start}
    directions = [(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)]
    if not allow_diagonal:
        directions = [(-1, 0), (1, 0), (0, -1), (0, 1)]
    while queue:
        x, y, path = queue.popleft()
        if (x, y) == goal:
            return path
        for dx, dy in directions:
            nx, ny = x + dx, y + dy
            if 0 <= nx < cols and 0 <= ny < rows and grid[ny][nx] >= 0 and (nx, ny) not in visited:
                visited.add((nx, ny))
                queue.append((nx, ny, path + [(nx, ny)]))
    return []


def get_backend_info() -> dict:
    """Get information about available backends."""
    return {
        "cpp_available": _cpp_available,
        "cuda_available": _cuda_available,
        "pathfind_available": _pathfind_available,
        "tensor_available": _tensor_available,
        "backend": "cuda" if _cuda_available else ("cpp" if _cpp_available else "python"),
    }