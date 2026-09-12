# Copyright (c) Ultrone Contributors. All rights reserved.
"""Adapter base — the port interface every external-system adapter follows."""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional


class BaseAdapter(ABC):
    """Minimal lifecycle contract for adapters (init, connect, close)."""

    name: str = "base"

    @abstractmethod
    def connect(self) -> bool:
        """Establish the underlying connection/client. Return success."""

    @abstractmethod
    def close(self) -> None:
        """Release the underlying connection/client."""

    @abstractmethod
    def health(self) -> Dict[str, Any]:
        """Return adapter health/status for observability."""

    def info(self) -> Dict[str, Any]:
        return {"adapter": self.name, "class": type(self).__name__}


def unavailable(reason: str) -> Dict[str, Any]:
    """Uniform 'not wired yet' response for placeholder adapters."""
    return {"available": False, "reason": reason}
