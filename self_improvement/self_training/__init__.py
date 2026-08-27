# Copyright (c) Ultrone Contributors. All rights reserved.
"""Self-training substrate for ULTRONE.

The controlled self-improvement cycle -- GENERATE -> EXECUTE ->
EVALUATE -> SELECT -> TRAIN -> VALIDATE -> COMPARE -> PROMOTE --
expressed as composable, deterministic, testable stages. Nothing here
lets production mutate itself: the incumbent model is only ever read;
candidates are fitted in a sandbox workdir and reach production only
through the governed gates + checkpoint manager.

``LearnedWeights`` is the serializable capability model (not a
foundation model); ``make_executor`` bridges it into the Orchestrator
seam so the whole adaptive + orchestration stack can be driven by
learned capability instead of ``_simulate_quality``.
"""

from self_improvement.self_training.adapters import (
    HostedModelAdapter,
    LocalModelAdapter,
    ModelAdapter,
    ModelOutput,
    TestModelAdapter,
)
from self_improvement.self_training.checkpoint import (
    CheckpointManager,
    ModelRecord,
)
from self_improvement.self_training.curriculum_manager import (
    CurriculumManager,
    CurriculumStep,
)
from self_improvement.self_training.dataset_builder import (
    ContinualMixture,
    DatasetArtifact,
    DatasetBuilder,
    TrainingExample,
)
from self_improvement.self_training.experience_selector import (
    ExperienceSelector,
    SelectedExperiences,
)
from self_improvement.self_training.evaluation import (
    CapabilityComparison,
    CapabilityMetrics,
    compare_capabilities,
    evaluate_capabilities,
)
from self_improvement.self_training.promotion import (
    Promoter,
    PromotionDecision,
)
from self_improvement.self_training.regression import (
    FamilyReport,
    RegressionReport,
    RegressionSuite,
)
from self_improvement.self_training.scheduler import Scheduler
from self_improvement.self_training.task_generator import (
    LevelSpec,
    default_curriculum,
)
from self_improvement.self_training.trainer import (
    FitResult,
    LearnedWeights,
    StatisticalTrainer,
    make_executor,
)

__all__ = [
    "HostedModelAdapter",
    "LocalModelAdapter",
    "ModelAdapter",
    "ModelOutput",
    "TestModelAdapter",
    "CheckpointManager",
    "CurriculumManager",
    "CurriculumStep",
    "ContinualMixture",
    "DatasetArtifact",
    "DatasetBuilder",
    "TrainingExample",
    "ExperienceSelector",
    "SelectedExperiences",
    "CapabilityComparison",
    "CapabilityMetrics",
    "compare_capabilities",
    "evaluate_capabilities",
    "Promoter",
    "PromotionDecision",
    "FamilyReport",
    "RegressionReport",
    "RegressionSuite",
    "Scheduler",
    "LevelSpec",
    "default_curriculum",
    "FitResult",
    "LearnedWeights",
    "StatisticalTrainer",
    "make_executor",
]