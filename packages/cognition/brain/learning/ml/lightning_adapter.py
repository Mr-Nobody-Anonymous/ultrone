"""PyTorch Lightning adapter for production-grade training."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

logger = logging.getLogger("Ultrone.Brain.Learning.ML.Lightning")


@dataclass
class LightningConfig:
    """Configuration for Lightning adapter."""
    max_epochs: int = 100
    devices: int = 1
    accelerator: str = "auto"
    precision: str = "32"


class LightningAdapter:
    """Adapter for PyTorch Lightning training.

    Enables distributed training, mixed precision, and
    checkpointing with a unified interface.

    Requires: ``pip install pytorch-lightning``
    """

    def __init__(self, config: Optional[LightningConfig] = None):
        self.config = config or LightningConfig()

    def train(self, model: Any, datamodule: Any) -> Dict[str, Any]:
        """Train a Lightning model."""
        try:
            import pytorch_lightning as pl
            trainer = pl.Trainer(
                max_epochs=self.config.max_epochs,
                devices=self.config.devices,
                accelerator=self.config.accelerator,
                precision=self.config.precision,
            )
            trainer.fit(model, datamodule)
            return {"status": "completed", "epochs": self.config.max_epochs}
        except ImportError:
            logger.warning("pytorch-lightning not installed.")
            return {"status": "skipped"}

    def get_stats(self) -> Dict[str, Any]:
        return {"type": "LightningAdapter"}
