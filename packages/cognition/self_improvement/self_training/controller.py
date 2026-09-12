# Copyright (c) Ultrone Contributors. All rights reserved.
"""The controlled self-training loop.

Owns one pass of::

    GENERATE -> EXECUTE -> EVALUATE -> SELECT -> TRAIN
    -> VALIDATE -> COMPARE -> PROMOTE

using the sibling modules, and never lets the production agent train
itself directly -- the production model is only ever *read* as
parent/baseline; the candidate is fitted in the sandbox directory and
enters production only through the promotion gates + checkpoint
manager.

How training signal avoids self-deception: only *good* experiences
(validator-accepted and above the quality bar) become examples, and
the trained candidate must beat baseline on a *holdout* family by the
Evaluator margin while the regression suite forbids breaking any
family. A cycle that would teach from weak experience produces no
dataset, hence no candidate, hence no promotion.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from orchestration.router import Orchestrator, RoutingPolicy
from orchestration.task_classifier import TaskProfile
from orchestration.traces import TraceLog

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
)
from self_improvement.self_training.experience_selector import (
    ExperienceSelector,
    SelectedExperiences,
)
from self_improvement.self_training.promotion import (
    Promoter,
    PromotionDecision,
)
from self_improvement.self_training.regression import (
    RegressionReport,
    RegressionSuite,
    build_families,
)
from self_improvement.self_training.scheduler import (
    Scheduler,
    ScheduleDecision,
)
from self_improvement.self_training.trainer import (
    LearnedWeights,
    StatisticalTrainer,
    make_executor,
)


def synthesize_weakness_examples(
        weakness: Dict[str, float],
        count: int = 2) -> List[Dict[str, Any]]:
    """Targeted practice: examples on exactly what failed recently.

    Weakness profile comes from the selector's bad bucket; each
    synthesized example re-poses that demand vector with an outcome
    score that asks the learner to meet it (approx. the good floor),
    so practice is aimed at the gap rather than spread uniformly.
    """
    if not weakness:
        return []
    domains = (weakness.get("domains") or "analysis").split(",")
    examples = []
    for index in range(count):
        examples.append({
            "example_id": f"synthetic-weak-{index}",
            "input": {
                "domain": domains[index % len(domains)],
                "difficulty": weakness.get("difficulty", 0.5),
                "reasoning_depth": weakness.get("reasoning_depth", 0.5),
                "context_requirement": weakness.get(
                    "context_requirement", 0.3),
                "tool_requirement": weakness.get("tool_requirement", 0.0),
                "latency_sensitivity": weakness.get(
                    "latency_sensitivity", 0.2),
                "privacy_required": False,
                "summary": "targeted weakness practice",
            },
            "context": {},
            "desired_behavior": {"accepted": True},
            "outcome_score": 0.60,
        })
    return examples


@dataclass
class CycleReport:
    cycle: int
    decision: ScheduleDecision
    mean_utility: float
    selected: SelectedExperiences
    dataset: Optional[DatasetArtifact] = None
    mixture: Optional[DatasetArtifact] = None
    candidate: Optional[LearnedWeights] = None
    regression: Optional[RegressionReport] = None
    promotion: Optional[PromotionDecision] = None
    checkpoint: Optional[ModelRecord] = None
    curriculum: Optional[CurriculumStep] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "cycle": self.cycle,
            "should_train": self.decision.should_train,
            "schedule_reason": self.decision.reason,
            "mean_utility": self.mean_utility,
            "selected": self.selected.counts() if self.selected else {},
            "dataset": self.dataset.to_dict() if self.dataset else None,
            "mixture": self.mixture.to_dict() if self.mixture else None,
            "candidate_hash": (self.candidate.model_hash
                               if self.candidate else None),
            "regression_passed": (self.regression.passed
                                  if self.regression else None),
            "promotion": {"decision": self.promotion.decision,
                          "reason": self.promotion.reason}
            if self.promotion else None,
            "checkpoint": self.checkpoint.model_id
            if self.checkpoint else None,
            "curriculum": self.curriculum.to_dict()
            if self.curriculum else None,
        }


#: Fresh starter weights (deliberately inconsistent so tasks vary).
_DEFAULT_STARTER = LearnedWeights(values={
    "reasoning": 0.52, "coding": 0.56, "retrieval": 0.46,
    "tool_use": 0.58})


class SelfTrainingController:
    """Closed loop: generate, learn, validate, promote -- never freely."""

    def __init__(self, *, workdir: str = "self_improvement/self_training",
                 policy: Optional[RoutingPolicy] = None,
                 starter: Optional[LearnedWeights] = None,
                 batch: int = 8,
                 good_floor: float = 0.50,
                 prior_strength: float = 2.0,
                 margin: float = 0.01,
                 min_good_examples: int = 3,
                 desired_ceiling: float = 0.85) -> None:
        self.policy = policy or RoutingPolicy()
        self._workdir = Path(workdir)
        self._workdir.mkdir(parents=True, exist_ok=True)
        self.checkpoints = CheckpointManager(str(self._workdir / "models"))
        self.curriculum = CurriculumManager()
        self.selector = ExperienceSelector(good_floor=good_floor)
        self.builder = DatasetBuilder(str(self._workdir / "datasets"))
        self.mixture_ratios = ContinualMixture()
        self.trainer = StatisticalTrainer(prior_strength=prior_strength)
        self.scheduler = Scheduler(min_good_examples=min_good_examples)
        families = build_families(n_each=6)
        self.suite = RegressionSuite(families=families)
        brain = None
        try:
            from adaptive.promotion import BrainStore
            brain = BrainStore(storage_dir=str(self._workdir / "brain"))
        except ImportError:               # pragma: no cover
            pass
        self.promoter = Promoter(holdout=families["unseen"],
                                 margin=margin, brain=brain)
        self.batch = int(batch)
        self._starter = starter or _DEFAULT_STARTER
        self._desired_ceiling = float(desired_ceiling)
        self._traces_dir = self._workdir / "traces"
        self._traces_dir.mkdir(parents=True, exist_ok=True)
        self._historical: Optional[DatasetArtifact] = None

    # -- the loop -------------------------------------------------------- #
    def run_cycle(self, cycle: int, *,
                  baseline: Optional[LearnedWeights] = None) -> CycleReport:
        current = baseline or self._current_model()
        profiles = self.curriculum.tasks(self.batch)
        outcomes, traces = self._execute(profiles, current, cycle)

        mean_utility = (sum(o.score for o in outcomes) / len(outcomes)
                        if outcomes else 0.0)
        selected = self.selector.select(traces)
        decision = self.scheduler.decide(
            len(selected.good), recent_rejected=0)
        outcome = CycleReport(cycle=cycle, decision=decision,
                              mean_utility=round(float(mean_utility), 6),
                              selected=selected)
        if not decision.should_train:
            return outcome

        dataset = self.builder.build_from_traces(
            selected.good, tag=f"cycle-{cycle}",
            desired_ceiling=self._desired_ceiling)
        weakness = selected.weakness_profile()
        synthesized = synthesize_weakness_examples(weakness)
        mixture = self.mixture_ratios.merge(
            self._historical, dataset, synthesized,
            workdir=str(self._workdir / "mixtures"),
            tag=f"cycle-{cycle}")
        self._historical = mixture
        if mixture is None:
            return outcome                   # no usable signal this cycle

        candidate = self.trainer.fit(mixture.load(), current).weights
        regression = self.suite.run(candidate, current)
        promotion = self.promoter.run(candidate, current, regression,
                                      persist=True)

        checkpoint: Optional[ModelRecord] = None
        parent = self.checkpoints.production()
        if promotion.promoted:
            checkpoint = self.checkpoints.register_candidate(
                candidate,
                dataset_hash=mixture.content_hash,
                configuration_hash=candidate.to_config()["kind"],
                training_seed=str(cycle),
                parent_model=parent.model_id if parent else "",
                duration_seconds=0.0)
            scores = {family: rep.mean_delta
                      for family, rep in regression.families.items()}
            self.checkpoints.evaluate(checkpoint.model_id, scores)
            self.checkpoints.promote(checkpoint.model_id)

        outcome.dataset = dataset
        outcome.mixture = mixture
        outcome.candidate = candidate
        outcome.regression = regression
        outcome.promotion = promotion
        outcome.checkpoint = checkpoint
        outcome.curriculum = self.curriculum.record(outcome.mean_utility)
        return outcome

    # -- helpers --------------------------------------------------------- #
    def _execute(self, profiles, current, cycle):
        """Run every profile under the current model; return outcomes+traces."""
        log = TraceLog(self._traces_dir / f"cycle-{cycle}.jsonl")
        orchestrator = Orchestrator(self.policy,
                                    executor=make_executor(current))
        outcomes = orchestrator.run_many(profiles, trace_log=log)
        return outcomes, log.load()

    def _current_model(self) -> LearnedWeights:
        return self.checkpoints.production_weights() or self._starter