# Copyright (c) Ultrone Contributors. All rights reserved.
"""Custom exceptions for the ULTRONE cognitive architecture."""

from __future__ import annotations

from typing import Any, Dict, Optional


class CognitiveError(Exception):
    """Base exception for all cognitive architecture errors."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}

    def __str__(self) -> str:
        if self.details:
            return f"{self.message} | details={self.details}"
        return self.message


class PerceptionError(CognitiveError):
    """Raised when perception processing fails."""


class WorldModelError(CognitiveError):
    """Raised when world model update or prediction fails."""


class ReasoningError(CognitiveError):
    """Raised when reasoning engine fails."""


class PlanningError(CognitiveError):
    """Raised when planning fails or produces invalid plans."""


class MemoryError(CognitiveError):
    """Raised when memory operations fail."""


class KnowledgeError(CognitiveError):
    """Raised when knowledge system operations fail."""


class SafetyError(CognitiveError):
    """Raised when safety monitors detect a violation requiring intervention."""


class UncertaintyError(CognitiveError):
    """Raised when uncertainty exceeds acceptable thresholds."""


class ActiveInferenceError(CognitiveError):
    """Raised when active inference computation fails."""


class SelfReflectionError(CognitiveError):
    """Raised when self-reflection analysis fails."""


class MetaLearningError(CognitiveError):
    """Raised when meta-learning adaptation fails."""


class AgenticError(CognitiveError):
    """Raised when agentic collaboration fails."""


class LearningError(CognitiveError):
    """Raised when learning operations fail."""


class ExplainabilityError(CognitiveError):
    """Raised when explainability generation fails."""
