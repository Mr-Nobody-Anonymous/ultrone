# Copyright (c) Ultrone Contributors. All rights reserved.
"""Experience database for feedback learning.

Stores user interactions with full context: prompt, model response, tools
used, retrieved documents, user correction, explicit rating, implicit
feedback, final accepted answer, and task category.
"""

from __future__ import annotations

import json
import logging
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("Ultrone.Learning.Feedback.ExperienceDB")


@dataclass
class InteractionRecord:
    """A single user interaction record."""

    interaction_id: str = field(default_factory=lambda: f"int-{uuid.uuid4().hex[:12]}")
    prompt: str = ""
    model_response: str = ""
    tools_used: List[str] = field(default_factory=list)
    retrieved_documents: List[str] = field(default_factory=list)
    user_correction: str = ""
    explicit_rating: Optional[float] = None  # 1-5
    implicit_feedback: float = 0.0  # -1 to 1
    final_accepted_answer: str = ""
    task_category: str = ""
    model_id: str = ""
    timestamp: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "interaction_id": self.interaction_id,
            "prompt": self.prompt,
            "model_response": self.model_response,
            "tools_used": self.tools_used,
            "retrieved_documents": self.retrieved_documents,
            "user_correction": self.user_correction,
            "explicit_rating": self.explicit_rating,
            "implicit_feedback": self.implicit_feedback,
            "final_accepted_answer": self.final_accepted_answer,
            "task_category": self.task_category,
            "model_id": self.model_id,
            "timestamp": self.timestamp,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "InteractionRecord":
        return cls(
            interaction_id=data.get("interaction_id", f"int-{uuid.uuid4().hex[:12]}"),
            prompt=data.get("prompt", ""),
            model_response=data.get("model_response", ""),
            tools_used=data.get("tools_used", []),
            retrieved_documents=data.get("retrieved_documents", []),
            user_correction=data.get("user_correction", ""),
            explicit_rating=data.get("explicit_rating"),
            implicit_feedback=data.get("implicit_feedback", 0.0),
            final_accepted_answer=data.get("final_accepted_answer", ""),
            task_category=data.get("task_category", ""),
            model_id=data.get("model_id", ""),
            timestamp=data.get("timestamp", time.time()),
            metadata=data.get("metadata", {}),
        )


class ExperienceDatabase:
    """Stores and queries user interaction records.

    Supports JSON persistence, filtering by task category, and building
    training datasets from interactions.
    """

    def __init__(self, storage_path: str = "learning/feedback/experiences.json"):
        self.storage_path = Path(storage_path)
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        self._records: Dict[str, InteractionRecord] = {}
        self._load()

    def add_interaction(self, record: InteractionRecord) -> InteractionRecord:
        """Add an interaction record."""
        self._records[record.interaction_id] = record
        self._save()
        return record

    def record(
        self,
        prompt: str,
        model_response: str = "",
        tools_used: Optional[List[str]] = None,
        retrieved_documents: Optional[List[str]] = None,
        user_correction: str = "",
        explicit_rating: Optional[float] = None,
        implicit_feedback: float = 0.0,
        final_accepted_answer: str = "",
        task_category: str = "",
        model_id: str = "",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> InteractionRecord:
        """Convenience method to create and store an interaction."""
        record = InteractionRecord(
            prompt=prompt,
            model_response=model_response,
            tools_used=tools_used or [],
            retrieved_documents=retrieved_documents or [],
            user_correction=user_correction,
            explicit_rating=explicit_rating,
            implicit_feedback=implicit_feedback,
            final_accepted_answer=final_accepted_answer or model_response,
            task_category=task_category,
            model_id=model_id,
            metadata=metadata or {},
        )
        return self.add_interaction(record)

    def get(self, interaction_id: str) -> Optional[InteractionRecord]:
        """Get an interaction by ID."""
        return self._records.get(interaction_id)

    def list_interactions(self) -> List[InteractionRecord]:
        """List all interactions."""
        return list(self._records.values())

    def filter_by_category(self, category: str) -> List[InteractionRecord]:
        """Filter interactions by task category."""
        return [r for r in self._records.values() if r.task_category == category]

    def filter_by_rating(self, min_rating: float = 4.0) -> List[InteractionRecord]:
        """Filter interactions by explicit rating."""
        return [r for r in self._records.values() if r.explicit_rating is not None and r.explicit_rating >= min_rating]

    def build_training_dataset(self, min_quality: float = 0.0) -> List[Dict[str, Any]]:
        """Build a training dataset from interactions.

        Returns a list of examples suitable for fine-tuning:
        {"prompt": ..., "response": ..., "preference": ...}
        """
        dataset = []
        for record in self._records.values():
            # Determine the best response (accepted answer or corrected)
            best_response = record.final_accepted_answer or record.user_correction or record.model_response
            if not best_response:
                continue

            # Compute a quality score
            quality = self._compute_quality(record)
            if quality < min_quality:
                continue

            example = {
                "prompt": record.prompt,
                "response": best_response,
                "preference": quality,
                "task_category": record.task_category,
                "model_id": record.model_id,
            }
            dataset.append(example)
        return dataset

    @staticmethod
    def _compute_quality(record: InteractionRecord) -> float:
        """Compute a quality score for an interaction."""
        score = 0.5  # neutral baseline
        if record.explicit_rating is not None:
            score = (record.explicit_rating - 1) / 4  # 1-5 → 0-1
        score += record.implicit_feedback * 0.3
        if record.user_correction:
            score += 0.1  # corrections are valuable signal
        return max(0.0, min(1.0, score))

    def get_stats(self) -> Dict[str, Any]:
        """Return database statistics."""
        return {
            "type": "ExperienceDatabase",
            "interactions": len(self._records),
            "with_rating": sum(1 for r in self._records.values() if r.explicit_rating is not None),
            "with_correction": sum(1 for r in self._records.values() if r.user_correction),
            "categories": len(set(r.task_category for r in self._records.values() if r.task_category)),
        }

    def _save(self) -> None:
        """Persist records to JSON."""
        data = [r.to_dict() for r in self._records.values()]
        with open(self.storage_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, default=str)

    def _load(self) -> None:
        """Load records from JSON."""
        if not self.storage_path.exists():
            return
        try:
            with open(self.storage_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            for item in data:
                record = InteractionRecord.from_dict(item)
                self._records[record.interaction_id] = record
        except Exception as exc:
            logger.warning("Failed to load experiences: %s", exc)