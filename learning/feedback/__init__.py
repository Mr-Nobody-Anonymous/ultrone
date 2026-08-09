# Copyright (c) Ultrone Contributors. All rights reserved.
"""Feedback Learning — user interaction learning pipeline.

Implements:
    User interaction → Feedback extraction → Preference signal →
    Quality classifier → Experience database → Training dataset →
    Evaluation → Fine-tuning / preference optimization

Stores prompt, model response, tools used, retrieved documents, user
correction, explicit rating, implicit feedback, final accepted answer,
and task category. Does NOT modify model weights directly after each
conversation — instead builds datasets for training jobs.
"""

from __future__ import annotations

from .experience_db import ExperienceDatabase, InteractionRecord
from .feedback_extractor import FeedbackExtractor, FeedbackSignal
from .preference_optimizer import PreferenceOptimizer

__all__ = [
    "ExperienceDatabase",
    "InteractionRecord",
    "FeedbackExtractor",
    "FeedbackSignal",
    "PreferenceOptimizer",
]