# Copyright (c) Ultrone Contributors. All rights reserved.
"""Ultrone Battlefield AI - Military C2 Simulation Framework."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

__all__ = ["Orchestrator", "MilitaryConfig"]
__version__ = "1.0.0"


def __getattr__(name: str) -> Any:
    if name == "Orchestrator":
        from .brain import Orchestrator as _Orchestrator
        return _Orchestrator
    if name == "MilitaryConfig":
        from .config import MilitaryConfig as _MilitaryConfig
        return _MilitaryConfig
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
