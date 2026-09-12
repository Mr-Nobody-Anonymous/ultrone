# Copyright (c) Ultrone Contributors. All rights reserved.
"""ultrone_rt -- deterministic high-performance runtime kernels.

Pure-Python reference implementations mirroring the Rust crate in
``rust/ultrone_core/`` one-to-one. ``ultrone_rt.loader`` selects the
compiled Rust backend when it has been built (maturin) and silently
falls back to these references otherwise, so behavior -- and tests --
are identical on every machine.
"""

from ultrone_rt.kernels import (
    CommandRouter,
    MemoryIndex,
    Simulator,
    SpatialIndex,
    TickScheduler,
    WorldState,
    batch_sphere_eval,
    cosine_similarity,
    dot_product,
    softmax,
    top_k_indices,
)
from ultrone_rt.loader import backend_info, get_kernels

__all__ = [
    "WorldState", "Simulator", "SpatialIndex", "TickScheduler",
    "CommandRouter", "MemoryIndex",
    "dot_product", "cosine_similarity", "softmax", "top_k_indices",
    "batch_sphere_eval",
    "get_kernels", "backend_info",
]
