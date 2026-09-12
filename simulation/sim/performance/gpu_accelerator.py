"""GPU-accelerated computation for simulation."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple

logger = logging.getLogger("Ultrone.Sim.Performance.GPU")


@dataclass
class GPUConfig:
    """Configuration for GPU acceleration."""
    device: str = "cuda"  # cuda, mps, cpu
    mixed_precision: bool = True
    memory_fraction: float = 0.8


class GPUAccelerator:
    """GPU-accelerated computation for batch simulation.

    Provides GPU-accelerated versions of expensive operations
    such as batch neural network inference, matrix operations,
    and parallel agent updates.

    Requires: PyTorch with CUDA or Metal Performance Shaders.
    """

    def __init__(self, config: Optional[GPUConfig] = None):
        self.config = config or GPUConfig()
        self._device = "cpu"

    def initialize(self) -> None:
        """Detect and initialize GPU device."""
        try:
            import torch
            if torch.cuda.is_available() and self.config.device == "cuda":
                self._device = "cuda"
                torch.cuda.set_per_process_memory_fraction(self.config.memory_fraction)
            elif hasattr(torch.backends, "mps") and torch.backends.mps.is_available() and self.config.device == "mps":
                self._device = "mps"
            logger.info("GPU accelerator using device: %s", self._device)
        except ImportError:
            logger.warning("PyTorch not available. GPU acceleration disabled.")

    @property
    def device(self) -> str:
        return self._device

    def get_stats(self) -> Dict[str, Any]:
        return {"type": "GPUAccelerator", "device": self._device}
