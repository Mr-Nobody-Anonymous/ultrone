"""Knowledge distillation for model compression and transfer."""

from __future__ import annotations

import logging
import numpy as np
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple

from .base import BaseMetaLearner, MetaLearningConfig, MetaTask

logger = logging.getLogger("Ultrone.Brain.Learning.MetaLearning.KnowledgeDistillation")


@dataclass
class DistillConfig(MetaLearningConfig):
    """Configuration for knowledge distillation."""
    temperature: float = 3.0
    alpha: float = 0.5  # balance between hard and soft targets
    student_hidden_dim: int = 32
    teacher_weight: float = 0.7


class KnowledgeDistillation(BaseMetaLearner):
    """Knowledge distillation from a teacher model to a student model."""

    def __init__(self, config: Optional[DistillConfig] = None):
        super().__init__(config or DistillConfig())
        self._teacher_params: Dict[str, np.ndarray] = {}
        self._student_params: Dict[str, np.ndarray] = {
            "weights": np.random.randn(64, self.config.student_hidden_dim) * 0.01,
            "output_weights": np.random.randn(self.config.student_hidden_dim, 1) * 0.01,
            "bias": np.zeros(1)
        }
        self._teacher_fn: Optional[Callable] = None

    def set_teacher(self, teacher_fn: Callable) -> None:
        """Set the teacher model function."""
        self._teacher_fn = teacher_fn

    def meta_fit(self, tasks: List[MetaTask]) -> None:
        """Distill knowledge from teacher to student."""
        if self._teacher_fn is None:
            logger.warning("No teacher model set. Use set_teacher() first.")
            return

        for iteration in range(self.config.num_meta_iterations):
            total_loss = 0.0
            for task in tasks[:self.config.batch_size]:
                x = task.support_inputs

                # Teacher predictions (soft targets)
                teacher_logits = self._teacher_fn(x)
                teacher_soft = self._softmax(teacher_logits / self.config.temperature)

                # Student predictions
                hidden = np.dot(x, self._student_params["weights"])
                student_logits = np.dot(hidden, self._student_params["output_weights"]) + self._student_params["bias"]
                student_soft = self._softmax(student_logits / self.config.temperature)

                # Hard targets (ground truth)
                hard_targets = task.support_targets
                if hard_targets.ndim == 1:
                    hard_targets = hard_targets[:, None]

                # Distillation loss
                soft_loss = self._kl_divergence(teacher_soft, student_soft)
                hard_loss = np.mean((student_logits - hard_targets) ** 2)
                loss = self.config.alpha * hard_loss + (1 - self.config.alpha) * soft_loss

                # Gradient computation (simplified)
                grad_output = 2 * (student_logits - hard_targets) / len(x)
                grad_hidden = np.dot(grad_output, self._student_params["output_weights"].T)
                grad_w_out = np.dot(hidden.T, grad_output)
                grad_b = np.mean(grad_output, axis=0)
                grad_w = np.dot(x.T, grad_hidden)

                self._student_params["output_weights"] -= self.config.outer_lr * grad_w_out
                self._student_params["bias"] -= self.config.outer_lr * grad_b
                self._student_params["weights"] -= self.config.outer_lr * grad_w

                total_loss += loss

            if iteration % 100 == 0:
                logger.info(f"Distillation iteration {iteration}: loss = {total_loss/len(tasks):.4f}")

        self._is_trained = True

    def adapt(self, task: MetaTask) -> None:
        """Fine-tune student on a specific task."""
        x, y = task.support_inputs, task.support_targets
        if x.size == 0 or y.size == 0:
            return

        for _ in range(self.config.num_inner_steps):
            hidden = np.dot(x, self._student_params["weights"])
            pred = np.dot(hidden, self._student_params["output_weights"]) + self._student_params["bias"]
            error = pred - y[:, None] if y.ndim == 1 else pred - y

            grad_output = 2 * error / len(x)
            grad_hidden = np.dot(grad_output, self._student_params["output_weights"].T)
            grad_w_out = np.dot(hidden.T, grad_output)
            grad_b = np.mean(grad_output, axis=0)
            grad_w = np.dot(x.T, grad_hidden)

            self._student_params["output_weights"] -= self.config.inner_lr * grad_w_out
            self._student_params["bias"] -= self.config.inner_lr * grad_b
            self._student_params["weights"] -= self.config.inner_lr * grad_w

    def predict(self, inputs: np.ndarray) -> np.ndarray:
        hidden = np.dot(inputs, self._student_params["weights"])
        return np.dot(hidden, self._student_params["output_weights"]) + self._student_params["bias"]

    def get_compression_ratio(self) -> float:
        """Get the compression ratio of student vs teacher."""
        student_params = sum(p.size for p in self._student_params.values())
        teacher_params = sum(p.size for p in self._teacher_params.values()) if self._teacher_params else 1
        return teacher_params / max(student_params, 1)

    @staticmethod
    def _softmax(x: np.ndarray) -> np.ndarray:
        exp_x = np.exp(x - np.max(x, axis=-1, keepdims=True))
        return exp_x / np.sum(exp_x, axis=-1, keepdims=True)

    @staticmethod
    def _kl_divergence(p: np.ndarray, q: np.ndarray) -> float:
        return float(np.sum(p * np.log(p / (q + 1e-8) + 1e-8)))

