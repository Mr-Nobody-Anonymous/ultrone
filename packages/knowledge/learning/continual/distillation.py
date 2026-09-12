# Copyright (c) Ultrone Contributors. All rights reserved.
"""Knowledge distillation for training compact student models.

Implements a distillation trainer that transfers knowledge from a
(pre-trained) teacher model to a smaller student model.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import torch
import torch.nn as nn
import torch.nn.functional as F

logger = logging.getLogger("Ultrone.Learning.Continual.Distillation")


@dataclass
class DistillationConfig:
    """Configuration for knowledge distillation."""
    teacher_model: Any  # Teacher model (must produce logits)
    student_model: Any  # Student model
    temperature: float = 4.0  # Softmax temperature
    alpha: float = 0.5         # Weight for distillation loss vs. CE loss
    max_epochs: int = 10
    learning_rate: float = 1e-4
    weight_decay: float = 1e-5
    batch_size: int = 32
    device: str = "auto"

    def get_device(self) -> torch.device:
        if self.device == "auto":
            return torch.device("cuda" if torch.cuda.is_available() else "cpu")
        return torch.device(self.device)


@dataclass
class DistillationDataset(torch.utils.data.Dataset):
    """Dataset of teacher-student input pairs with teacher logits."""
    inputs: List[torch.Tensor]
    teacher_logits: List[torch.Tensor]
    student_targets: Optional[List[torch.Tensor]] = None

    def __len__(self) -> int:
        return len(self.inputs)

    def __getitem__(self, idx: int):
        return {
            "input": self.inputs[idx],
            "teacher_logits": self.teacher_logits[idx],
            "target": self.student_targets[idx] if self.student_targets else None,
        }


class DistillationTrainer:
    """Trains a student model to distill knowledge from a teacher model.

    Uses KL divergence between softened teacher and student distributions
    combined with standard cross-entropy loss.
    """

    def __init__(self, config: DistillationConfig):
        self.config = config
        self.device = config.get_device()
        self.teacher = config.teacher_model.to(self.device)
        self.student = config.student_model.to(self.device)

        # Freeze teacher
        for param in self.teacher.parameters():
            param.requires_grad = False
        self.teacher.eval()

        self.optimizer = torch.optim.AdamW(
            self.student.parameters(),
            lr=config.learning_rate,
            weight_decay=config.weight_decay,
        )
        self.history: List[Dict[str, float]] = []

    def compute_teacher_logits(self, inputs: torch.Tensor) -> torch.Tensor:
        """Get soft labels from the teacher model (deterministic)."""
        with torch.no_grad():
            outputs = self.teacher(inputs)
            if hasattr(outputs, "logits"):
                return outputs.logits
            return outputs

    def distillation_loss(
        self,
        student_logits: torch.Tensor,
        teacher_logits: torch.Tensor,
        targets: Optional[torch.Tensor] = None,
    ) -> Dict[str, float]:
        """Compute combined distillation + CE loss.

        L = alpha * T^2 * KL(softmax(teacher/T) || softmax(student/T))
            + (1 - alpha) * CE(student, targets)
        """
        T = self.config.temperature
        alpha = self.config.alpha

        # KL divergence on softened distributions
        s_log_probs = F.log_softmax(student_logits / T, dim=-1)
        t_probs = F.softmax(teacher_logits / T, dim=-1)
        kl_loss = F.kl_div(s_log_probs, t_probs, reduction="batchmean") * (T * T)

        loss = alpha * kl_loss

        ce_loss = 0.0
        if targets is not None:
            ce = F.cross_entropy(student_logits, targets)
            loss = loss + (1 - alpha) * ce
            ce_loss = ce.item()

        return {"loss": loss, "distillation_loss": kl_loss.item(), "ce_loss": ce_loss}

    def train(
        self,
        dataset: DistillationDataset,
        epochs: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Run the distillation training loop.

        Returns training history with per-epoch metrics.
        """
        epochs = epochs or self.config.max_epochs
        loader = torch.utils.data.DataLoader(
            dataset, batch_size=self.config.batch_size, shuffle=True
        )

        self.student.train()
        for epoch in range(epochs):
            epoch_losses = []
            for batch in loader:
                inputs = batch["input"].to(self.device)
                teacher_logits = batch["teacher_logits"].to(self.device)
                targets = batch["target"].to(self.device) if batch["target"] is not None else None

                self.student.train()
                student_logits = self.student(inputs)
                if hasattr(student_logits, "logits"):
                    student_logits = student_logits.logits

                losses = self.distillation_loss(student_logits, teacher_logits, targets)

                self.optimizer.zero_grad()
                losses["loss"].backward()
                self.optimizer.step()
                epoch_losses.append(losses["loss"].item())

            avg_loss = sum(epoch_losses) / max(len(epoch_losses), 1)
            record = {"epoch": epoch, "avg_loss": avg_loss, "distillation_loss": 0.0, "ce_loss": 0.0}
            self.history.append(record)
            logger.info("Distillation epoch %d: loss=%.4f", epoch, avg_loss)

        return {
            "final_loss": self.history[-1]["avg_loss"] if self.history else 0.0,
            "epochs_completed": len(self.history),
            "history": self.history,
        }

    def evaluate(
        self,
        dataset: DistillationDataset,
    ) -> Dict[str, float]:
        """Evaluate student model on a dataset."""
        self.student.eval()
        loader = torch.utils.data.DataLoader(
            dataset, batch_size=self.config.batch_size, shuffle=False
        )
        total_loss = 0.0
        total_correct = 0
        total_samples = 0
        with torch.no_grad():
            for batch in loader:
                inputs = batch["input"].to(self.device)
                teacher_logits = batch["teacher_logits"].to(self.device)
                targets = batch["target"].to(self.device) if batch["target"] is not None else None
                student_logits = self.student(inputs)
                if hasattr(student_logits, "logits"):
                    student_logits = student_logits.logits
                losses = self.distillation_loss(student_logits, teacher_logits, targets)
                total_loss += losses["loss"].item()
                if targets is not None:
                    preds = student_logits.argmax(dim=-1)
                    total_correct += (preds == targets).sum().item()
                    total_samples += targets.size(0)

        return {
            "avg_loss": total_loss / max(len(loader), 1),
            "accuracy": total_correct / max(total_samples, 1),
        }

    def get_stats(self) -> Dict[str, Any]:
        teacher_params = sum(p.numel() for p in self.teacher.parameters())
        student_params = sum(p.numel() for p in self.student.parameters())
        return {
            "teacher_params": teacher_params,
            "student_params": student_params,
            "param_reduction": 1 - student_params / max(teacher_params, 1),
            "temperature": self.config.temperature,
            "alpha": self.config.alpha,
            "epochs_completed": len(self.history),
        }
