# Copyright (c) Ultrone Contributors. All rights reserved.
"""ULTRONE Cockpit backend.

Exposes the second-generation runtime (UDIS, MCP 2026-07-28, causal boundary,
event sourcing, scientific benchmarking, governance) to the operator/researcher
cockpit UI as a single, honest, machine-readable contract.

Nothing in this package fabricates state. Every value surfaced to the UI is read
from a real subsystem object or is the output of the deterministic simulation in
:mod:`apps.api.cockpit.world`.
"""

from __future__ import annotations

__all__ = ["get_runtime", "CockpitRuntime"]


def __getattr__(name: str):  # pragma: no cover - lazy re-export avoids import cycles
    if name in ("get_runtime", "CockpitRuntime"):
        from .runtime import CockpitRuntime, get_runtime

        return {"get_runtime": get_runtime, "CockpitRuntime": CockpitRuntime}[name]
    raise AttributeError(name)
