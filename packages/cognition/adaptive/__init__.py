# Copyright (c) Ultrone Contributors. All rights reserved.
"""Adaptive engine: bounded, benchmark-gated self-improvement.

Layers
------
- :mod:`adaptive.parameter_registry` -- typed parameters with bounds,
  defaults, versions, dependencies; the ONLY path to change tunables.
- :mod:`adaptive.evaluator` -- deterministic evaluation tasks and
  baseline-vs-candidate comparison with reproducibility + margin gates.
- :mod:`adaptive.optimizer` -- seeded evolutionary search over
  candidate configurations (never production state).
- :mod:`adaptive.promotion` -- PromotionGate + BrainStore: candidates
  reach ``production`` only through audited promotable records, across
  versioned channels (baseline/candidate/experimental/production).
- :mod:`adaptive.skill_library` -- reusable skills scored by benchmark
  and updated by real outcomes.
- :mod:`adaptive.experiment` -- grid experiments over single parameters.

Design rule (from the research charter): more parameters != more
intelligence. This layer exists to find *better configurations* under
evaluation, never to grow unconstrained.
"""

from adaptive.evaluator import (
    EvaluationResult,
    Evaluator,
    ground_patrol_score,
)
from adaptive.experiment import Experiment, ExperimentRunner, Trial
from adaptive.optimizer import (
    AdaptiveOptimizer,
    Candidate,
    OptimizationResult,
    default_patrol_registry,
)
from adaptive.parameter_registry import ParameterRegistry, ParameterSpec
from adaptive.promotion import BrainStore, PromotionGate, PromotionRecord
from adaptive.skill_library import Skill, SkillLibrary

__all__ = [
    # registry
    "ParameterRegistry", "ParameterSpec",
    # evaluation
    "Evaluator", "EvaluationResult", "ground_patrol_score",
    # optimization
    "AdaptiveOptimizer", "Candidate", "OptimizationResult",
    "default_patrol_registry",
    # promotion / versioning
    "PromotionGate", "PromotionRecord", "BrainStore",
    # skills
    "Skill", "SkillLibrary",
    # experiments
    "Experiment", "ExperimentRunner", "Trial",
]