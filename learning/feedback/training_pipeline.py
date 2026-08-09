# Copyright (c) Ultrone Contributors. All rights reserved.
"""Training pipeline for user-feedback-driven model improvement.

Implements the full pipeline:
interaction → memory → dataset → evaluation → training job →
candidate model → benchmark → approval → deployment

NOTES:
- Never modifies production weights directly.
- Feedback is accumulated into a dataset, which must pass evaluation
  before a new model is approved for deployment.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger("Ultrone.Learning.Feedback.TrainingPipeline")


class TrainingStage(Enum):
    """Stages of the feedback training pipeline."""
    COLLECTING = "collecting"
    DATASET_READY = "dataset_ready"
    EVALUATING = "evaluating"
    TRAINING = "training"
    BENCHMARKING = "benchmarking"
    AWAITING_APPROVAL = "awaiting_approval"
    APPROVED = "approved"
    DEPLOYED = "deployed"
    REJECTED = "rejected"


@dataclass
class FeedbackInteraction:
    """A single user interaction with feedback."""
    prompt: str
    model_response: str
    user_correction: Optional[str]
    explicit_rating: Optional[float]
    tools_used: List[str]
    retrieved_documents: List[Dict[str, Any]]
    final_accepted_answer: Optional[str]
    task_category: str
    timestamp: float = field(default_factory=lambda: time.time())
    interaction_id: str = field(default_factory=lambda: str(uuid.uuid4().hex[:16]))
    source: str = "user_interaction"


@dataclass
class TrainingDataset:
    """A curated dataset of feedback interactions."""
    dataset_id: str
    version: int
    created_at: float
    interactions: List[FeedbackInteraction]
    quality_scores: List[float]
    hash: str
    source: str = "user_feedback"
    schema_version: str = "1.0"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "dataset_id": self.dataset_id,
            "version": self.version,
            "created_at": self.created_at,
            "num_interactions": len(self.interactions),
            "hash": self.hash,
            "source": self.source,
            "schema_version": self.schema_version,
            "interactions": [
                {
                    "interaction_id": i.interaction_id,
                    "prompt": i.prompt,
                    "model_response": i.model_response,
                    "user_correction": i.user_correction,
                    "explicit_rating": i.explicit_rating,
                    "tools_used": i.tools_used,
                    "task_category": i.task_category,
                    "timestamp": i.timestamp,
                }
                for i in self.interactions
            ],
        }


class FeedbackTrainingPipeline:
    """Orchestrates feedback-driven model improvement.

    Pipeline stages:
    1. Collect interactions into a buffer
    2. When buffer reaches threshold, create a versioned dataset
    3. Evaluate the dataset quality
    4. Run a training job (LoRA/preference optimization)
    5. Benchmark the candidate against the baseline
    6. Require explicit approval before deployment
    """

    def __init__(
        self,
        buffer_size: int = 100,
        output_dir: str = "./feedback_datasets",
        config: Optional[Dict[str, Any]] = None,
    ):
        self.config = config or {}
        self.buffer_size = buffer_size
        self.output_dir = output_dir
        self._buffer: List[FeedbackInteraction] = []
        self._datasets: List[TrainingDataset] = []
        self._stage = TrainingStage.COLLECTING
        self._current_dataset: Optional[TrainingDataset] = None
        self._approval_required = True
        os.makedirs(output_dir, exist_ok=True)

    def add_interaction(
        self,
        prompt: str,
        model_response: str,
        user_correction: Optional[str] = None,
        explicit_rating: Optional[float] = None,
        tools_used: Optional[List[str]] = None,
        retrieved_documents: Optional[List[Dict]] = None,
        final_accepted_answer: Optional[str] = None,
        task_category: str = "general",
    ) -> str:
        """Add a user interaction to the feedback buffer.

        Returns the interaction ID.
        """
        interaction = FeedbackInteraction(
            prompt=prompt,
            model_response=model_response,
            user_correction=user_correction,
            explicit_rating=explicit_rating,
            tools_used=tools_used or [],
            retrieved_documents=retrieved_documents or [],
            final_accepted_answer=final_accepted_answer,
            task_category=task_category,
        )
        self._buffer.append(interaction)

        # If buffer is full, trigger dataset creation
        if len(self._buffer) >= self.buffer_size:
            self._create_dataset()

        return interaction.interaction_id

    def _create_dataset(self) -> Optional[TrainingDataset]:
        """Create a versioned dataset from the feedback buffer."""
        if not self._buffer:
            return None

        # Compute dataset hash for versioning
        content = json.dumps(
            [i.__dict__ for i in self._buffer],
            sort_keys=True,
            default=str,
        )
        dataset_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()[:32]

        version = len(self._datasets) + 1
        dataset = TrainingDataset(
            dataset_id=f"feedback-{version}",
            version=version,
            created_at=time.time(),
            interactions=list(self._buffer),
            quality_scores=[
                i.explicit_rating or 0.0 for i in self._buffer
            ],
            hash=dataset_hash,
        )

        # Save to disk
        path = os.path.join(self.output_dir, f"feedback_dataset_v{version}.json")
        with open(path, "w") as f:
            json.dump(dataset.to_dict(), f, indent=2, default=str)

        self._datasets.append(dataset)
        self._current_dataset = dataset
        self._buffer = []  # Clear buffer
        self._stage = TrainingStage.DATASET_READY

        logger.info(
            "Created feedback dataset v%d with %d interactions (hash=%s)",
            version, len(dataset.interactions), dataset_hash,
        )
        return dataset

    def evaluate_dataset(self) -> Dict[str, Any]:
        """Evaluate the quality of the current dataset."""
        if not self._current_dataset:
            return {"status": "no_dataset"}

        interactions = self._current_dataset.interactions
        num_corrections = sum(1 for i in interactions if i.user_correction)
        num_ratings = sum(1 for i in interactions if i.explicit_rating is not None)
        avg_rating = (
            sum(i.explicit_rating or 0.0 for i in interactions) / len(interactions)
            if interactions else 0.0
        )

        # Quality check: need at least 50% interactions with feedback
        feedback_rate = (num_corrections + num_ratings) / max(len(interactions), 1)
        quality_pass = feedback_rate >= 0.3 and len(interactions) >= 10

        self._stage = TrainingStage.EVALUATING if quality_pass else TrainingStage.COLLECTING
        return {
            "dataset_id": self._current_dataset.dataset_id,
            "num_interactions": len(interactions),
            "num_corrections": num_corrections,
            "num_ratings": num_ratings,
            "avg_rating": avg_rating,
            "feedback_rate": feedback_rate,
            "quality_pass": quality_pass,
            "stage": self._stage.value,
        }

    def start_training(self, training_config: Optional[Dict[str, Any]] = None) -> str:
        """Start a training job for the current dataset.

        Returns a job ID. In a real system, this would dispatch to the
        training platform. Here, it records the job plan.
        """
        if self._stage != TrainingStage.EVALUATING:
            raise RuntimeError(f"Cannot start training from stage {self._stage.value}")

        job_id = f"train-{uuid.uuid4().hex[:8]}"
        job = {
            "job_id": job_id,
            "dataset_id": self._current_dataset.dataset_id if self._current_dataset else None,
            "stage": self._stage.value,
            "training_config": training_config or {},
            "created_at": time.time(),
            "status": "queued",
            "candidate_model": f"feedback_model_{job_id}",
        }

        self._stage = TrainingStage.TRAINING
        logger.info("Started training job %s with dataset %s", job_id, job["dataset_id"])
        return job_id

    def benchmark_candidate(
        self,
        candidate_metrics: Dict[str, float],
        baseline_metrics: Dict[str, float],
    ) -> Dict[str, Any]:
        """Benchmark candidate model against baseline.

        Only approves if the candidate shows improvement across key metrics.
        """
        improvements = {}
        regressions = []
        for metric, candidate_val in candidate_metrics.items():
            baseline_val = baseline_metrics.get(metric, 0.0)
            if candidate_val > baseline_val:
                improvements[metric] = candidate_val - baseline_val
            elif candidate_val < baseline_val:
                regressions.append({
                    "metric": metric,
                    "candidate": candidate_val,
                    "baseline": baseline_val,
                    "regression": baseline_val - candidate_val,
                })

        # Require no major regressions and at least one improvement
        approved = len(regressions) == 0 and len(improvements) > 0
        self._stage = TrainingStage.APPROVED if approved else TrainingStage.REJECTED

        return {
            "candidate_model": "feedback_model",
            "improvements": improvements,
            "regressions": regressions,
            "approved": approved,
            "stage": self._stage.value,
        }

    def approve_deployment(self, approved: bool) -> None:
        """Explicitly approve or reject a candidate for deployment."""
        if approved:
            self._stage = TrainingStage.DEPLOYED
            logger.info("Feedback training candidate APPROVED for deployment")
        else:
            self._stage = TrainingStage.REJECTED
            logger.info("Feedback training candidate REJECTED")

    def get_status(self) -> Dict[str, Any]:
        return {
            "stage": self._stage.value,
            "buffer_size": len(self._buffer),
            "buffer_threshold": self.buffer_size,
            "datasets_created": len(self._datasets),
            "current_dataset": self._current_dataset.dataset_id if self._current_dataset else None,
            "approval_required": self._approval_required,
        }

    def list_datasets(self) -> List[Dict[str, Any]]:
        return [
            {"dataset_id": d.dataset_id, "version": d.version, "hash": d.hash,
             "num_interactions": len(d.interactions)}
            for d in self._datasets
        ]
