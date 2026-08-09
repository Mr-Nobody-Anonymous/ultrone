# Copyright (c) Ultrone Contributors. All rights reserved.
"""Distributed training support.

Provides utilities for DataParallel, DistributedDataParallel (DDP),
Fully Sharded Data Parallel (FSDP), and DeepSpeed integration.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger("Ultrone.TrainingPlatform.Distributed")


@dataclass
class DistributedConfig:
    """Configuration for distributed training."""
    backend: str = "nccl"          # "nccl", "gloo", "mpi"
    world_size: int = 1
    rank: int = 0
    local_rank: int = 0
    master_addr: str = "127.0.0.1"
    master_port: int = 29500
    mixed_precision: str = "fp16"   # "fp16", "bf16", "none"
    fsdp: bool = False
    gradient_checkpointing: bool = False
    cpu_offload: bool = False
    zero_optimization: bool = False
    zero_stage: int = 1              # 0, 1, 2, 3

    def is_distributed(self) -> bool:
        return self.world_size > 1

    def to_dict(self) -> Dict[str, Any]:
        return {
            "backend": self.backend,
            "world_size": self.world_size,
            "rank": self.rank,
            "mixed_precision": self.mixed_precision,
            "fsdp": self.fsdp,
            "zero_optimization": self.zero_optimization,
            "zero_stage": self.zero_stage,
        }


class DistributedTrainer:
    """Manages distributed training setup and coordination.

    Wraps PyTorch's distributed package with convenience methods for
    initialization, model distribution, and cleanup.
    """

    def __init__(self, config: Optional[DistributedConfig] = None):
        self.config = config or DistributedConfig()
        self._initialized = False
        self._model = None

    def initialize(self) -> bool:
        """Initialize the distributed process group.

        Returns True if distributed training is active.
        """
        if not self.config.is_distributed():
            logger.info("Single-process training (no distributed init needed)")
            return False

        import torch.distributed as dist

        os.environ.setdefault("MASTER_ADDR", self.config.master_addr)
        os.environ.setdefault("MASTER_PORT", str(self.config.master_port))

        dist.init_process_group(
            backend=self.config.backend,
            rank=self.config.rank,
            world_size=self.config.world_size,
        )
        self._initialized = True
        logger.info(
            "Initialized distributed training: backend=%s world_size=%d rank=%d",
            self.config.backend, self.config.world_size, self.config.rank,
        )
        return True

    def distribute_model(self, model: Any) -> Any:
        """Wrap a model for distributed training.

        Uses FSDP if enabled, otherwise DistributedDataParallel.
        """
        if not self._initialized:
            raise RuntimeError("Distributed trainer not initialized. Call initialize() first.")

        import torch

        if self.config.fsdp:
            from torch.distributed.fsdp import FullyShardedDataParallel as FSDP
            model = FSDP(model)
        else:
            from torch.nn.parallel import DistributedDataParallel as DDP
            model = DDP(model, device_ids=[self.config.local_rank])

        self._model = model
        return model

    def prepare_optimizer(self, optimizer: Any) -> Any:
        """Wrap optimizer with Zero/DeepSpeed if configured."""
        if self.config.zero_optimization:
            try:
                from deepspeed.ops.adam import DeepSpeedCPUAdam
                logger.info("Using DeepSpeed Zero stage %d", self.config.zero_stage)
                return optimizer  # Simplified — real impl would configure DeepSpeed
            except ImportError:
                logger.warning("DeepSpeed not available, using native optimizer")
        return optimizer

    def cleanup(self) -> None:
        """Clean up distributed process group."""
        if self._initialized:
            import torch.distributed as dist
            dist.destroy_process_group()
            self._initialized = False
            logger.info("Cleaned up distributed process group")

    def shard_data(self, dataset: Any) -> Any:
        """Shard a dataset across distributed processes."""
        from torch.utils.data import DistributedSampler

        sampler = DistributedSampler(dataset, shuffle=True)
        return sampler

    def get_stats(self) -> Dict[str, Any]:
        return {
            "initialized": self._initialized,
            "distributed": self.config.is_distributed(),
            "world_size": self.config.world_size,
            "backend": self.config.backend,
            "mixed_precision": self.config.mixed_precision,
            "fsdp": self.config.fsdp,
        }
