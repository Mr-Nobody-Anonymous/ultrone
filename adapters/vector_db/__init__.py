# Copyright (c) Ultrone Contributors. All rights reserved.
"""Vector database adapters — port for embedding stores.

Concrete wiring should wrap ``knowledge_engine.vector_memory`` and
``memory_cluster`` (duckdb/redis backends). No store logic lives here.
"""
from adapters.base import BaseAdapter, unavailable
from typing import Any, Dict

__all__ = ["VectorDBAdapter"]


class VectorDBAdapter(BaseAdapter):
    """Port every vector-store implementation must satisfy."""

    name = "vector_db"

    def connect(self) -> bool:  # pragma: no cover - placeholder
        return False

    def close(self) -> None:  # pragma: no cover - placeholder
        pass

    def health(self) -> Dict[str, Any]:  # pragma: no cover - placeholder
        return unavailable("no store implementation wired; see "
                           "knowledge_engine/vector_memory and memory_cluster")
