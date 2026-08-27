# Copyright (c) Ultrone Contributors. All rights reserved.
"""Bridge reflection traces into candidate registry overrides.

The reflection engine produces *qualitative* feedback (issues,
suggestions, a score trajectory). The adaptive engine consumes
*quantitative* registry overrides. Without a translator between them,
reflection and candidate generation are two islands and the closed loop
has a gap.

This adapter is intentionally:

- **Deterministic** -- the same (trace, registry) pair always yields
  the same override dict, so the closed-loop test is reproducible.
- **Backend-agnostic** -- no LLM required. The heuristic is a small
  mapping from feedback keywords to registry parameter deltas. It is
  safe to swap in a learned policy later because the function signature
  is stable.
- **Bounds-respecting** -- every override is validated against the
  target ``ParameterRegistry`` before being returned, so the bridge
  can never propose an undeclared or out-of-bounds value.
"""

from __future__ import annotations

import re
from typing import Any, Dict, Iterable, List, Optional, Tuple

from adaptive.parameter_registry import ParameterRegistry
from frontier.adaptation.reflection_engine import ReflectionTrace


# Numeric parameters the bridge is allowed to touch. Each entry pairs a
# parameter name with a tuple of hint tokens; the first tunable whose
# name contains any hint token is chosen for a given direction.
_NUMERIC_HINTS: Dict[str, Tuple[str, ...]] = {
    "patrol.speed": ("speed", "fast", "slow"),
    "patrol.wear_sensitivity": ("wear", "damage"),
    "patrol.waypoint_budget": ("budget", "time", "patient"),
}


def _direction(feedback: str) -> str:
    """Return ``"increase"`` / ``"decrease"`` / ``"none"`` for a feedback string."""
    text = feedback.lower()
    if "too slow" in text:
        return "increase"
    if "too fast" in text or "overshoot" in text:
        return "decrease"
    if "wear" in text or "damage" in text or "energy" in text:
        return "decrease"
    if "budget" in text or "more time" in text or "patient" in text:
        return "increase"
    if "slow" in text or "slower" in text or "conservative" in text:
        return "decrease"
    if "aggressive" in text:
        return "increase"
    return "none"


def _pick_parameter(direction: str,
                    tunable: Iterable[str]) -> Optional[str]:
    """Pick the first tunable parameter whose hint vocabulary matches."""
    direction_hints: Dict[str, Tuple[str, ...]] = {
        "increase": ("speed", "budget", "time", "patient", "aggressive"),
        "decrease": ("wear", "damage", "energy", "slow", "slower",
                      "conservative", "fast", "overshoot"),
    }
    wanted = direction_hints.get(direction, ())
    for name in tunable:
        lowered = name.lower()
        for hint in wanted:
            if hint in lowered:
                return name
    return None


def _delta(name: str, direction: str, registry: ParameterRegistry) -> Any:
    """Compute a small, bounded delta for a parameter."""
    spec = registry.spec(name)
    lo, hi = spec.bounds or (0.0, 1.0)
    span = float(hi) - float(lo)
    step = 0.05 * span
    current = registry.get(name)
    if spec.type == "int":
        step = max(1.0, round(step))
    if direction == "increase":
        new_value = current + step
    elif direction == "decrease":
        new_value = current - step
    else:
        return current
    if spec.type == "int":
        return int(round(new_value))
    return round(float(new_value), 4)
