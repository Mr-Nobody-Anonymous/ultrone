"""Abstract base class for all meta-learning algorithms."""

from __future__ import annotations

import logging
import numpy as np
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("Ultrone.Brain.Learning.MetaLearning.Base")


@dataclass
class MetaLearningConfig:
    """Base configuration for meta-learners."""
    inner_lr: float = 0.01
    outer_lr: float = 0.001
    num_inner_steps: int = 5
    num_meta_iterations: int = 1000
    batch_size: int = 16
    device: str = "cpu"


@dataclass
class MetaTask:
    """A task for meta-learning containing support and query sets."""
    task_id: str = ""
    support_inputs: np.ndarray = field(default_factory=lambda: np.array([]))
    support_targets: np.ndarray = field(default_factory=lambda: np.array([]))
    query_inputs: np.ndarray = field(default_factory=lambda: np.array([]))
    query_targets: np.ndarray = field(default_factory=lambda: np.array([]))
    metadata: Dict[str, Any] = field(default_factory=dict)


class BaseMetaLearner(ABC):
    """Abstract interface for meta-learning algorithms."""

    def __init__(self, config: MetaLearningConfig):
        self.config = config
        self._meta_parameters: Dict[str, np.ndarray] = {}
        self._is_trained = False

    @abstractmethod
    def meta_fit(self, tasks: List[MetaTask]) -> None:
        """Train on a distribution of tasks."""
        ...

    @abstractmethod
    def adapt(self, task: MetaTask) -> None:
        """Adapt to a new task with few examples."""
        ...

    @abstractmethod
    def predict(self, inputs: np.ndarray) -> np.ndarray:
        """Make predictions after adaptation."""
        ...

    def get_stats(self) -> Dict[str, Any]:
        return {
            "type": type(self).__name__,
            "is_trained": self._is_trained,
            "inner_lr": self.config.inner_lr,
            "outer_lr": self.config.outer_lr,
        }

