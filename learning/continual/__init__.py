"""Continual learning — replay buffers, LoRA, adapters, distillation."""
from .replay_buffer import ReplayBuffer, PrioritizedReplayBuffer
from .lora import LoRAAdapter, LoRAConfig
from .adapter import AdapterModule, AdapterConfig
from .distillation import DistillationTrainer, DistillationDataset

__all__ = [
    "ReplayBuffer",
    "PrioritizedReplayBuffer",
    "LoRAAdapter",
    "LoRAConfig",
    "AdapterModule",
    "AdapterConfig",
    "DistillationTrainer",
    "DistillationDataset",
]
