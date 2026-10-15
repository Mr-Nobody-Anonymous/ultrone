# Copyright (c) Ultrone Contributors. All rights reserved.
"""Ultrone top-level package compatibility shim."""

from __future__ import annotations

from apps.api.ultrone import Ultrone
from brain.orchestrator import Orchestrator
from config import MilitaryConfig

__all__ = ["Ultrone", "Orchestrator", "MilitaryConfig"]
__version__ = "1.0.0"
