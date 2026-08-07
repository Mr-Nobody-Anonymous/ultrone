# Copyright (c) Ultrone Contributors. All rights reserved.
"""Frontier Adaptation — Reflection, Self-Correction, and Critic.

Provides the self-improvement machinery that sits on top of the frontier
reasoning strategies:

- :class:`CriticModel`: scores and critiques solutions.
- :class:`ReflectionEngine`: generate → reflect → improve loop.
- :class:`SelfCorrectionEngine`: generate → verify → correct loop.

All components are backend-agnostic (driven by a ``Solver`` / ``Verifier``)
and never hardcode benchmark answers.
"""

from .critic_model import Critique, CriticModel
from .reflection_engine import ReflectionConfig, ReflectionEngine, ReflectionTrace
from .self_correction_engine import (
    CorrectionAttempt,
    SelfCorrectionConfig,
    SelfCorrectionEngine,
)

__all__ = [
    "Critique",
    "CriticModel",
    "ReflectionConfig",
    "ReflectionEngine",
    "ReflectionTrace",
    "CorrectionAttempt",
    "SelfCorrectionConfig",
    "SelfCorrectionEngine",
]
