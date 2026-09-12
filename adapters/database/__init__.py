# Copyright (c) Ultrone Contributors. All rights reserved.
"""Database adapters — port for persistent storage.

Concrete wiring should wrap ``core.database`` and the ``core.db_*`` modules,
plus ``research.research_db`` for the research catalog. No ORM logic lives
here.
"""
from adapters.base import BaseAdapter, unavailable
from typing import Any, Dict

__all__ = ["DatabaseAdapter"]


class DatabaseAdapter(BaseAdapter):
    """Port every database implementation must satisfy."""

    name = "database"

    def connect(self) -> bool:  # pragma: no cover - placeholder
        return False

    def close(self) -> None:  # pragma: no cover - placeholder
        pass

    def health(self) -> Dict[str, Any]:  # pragma: no cover - placeholder
        return unavailable("no database implementation wired; see "
                           "core/database and research/research_db")
