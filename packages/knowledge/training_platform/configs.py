# Copyright (c) Ultrone Contributors. All rights reserved.
"""Training platform configuration."""

from __future__ import annotations

from dataclasses import dataclass, field, asdict, fields as dataclasses_fields
from typing import Any, Dict, List, Optional

try:
    import yaml
except ImportError:
    yaml = None


@dataclass
class OptimizerConfig:
    """Optimizer configuration."""
    name: str = "adamw"
    learning_rate: float = 1e-4
    weight_decay: str = "0.01"
    betas: tuple = (0.9, 0.999)
    eps: float = 1e-8
    amsgrad: bool = False


@dataclass
class SchedulerConfig:
    """Learning rate scheduler configuration."""
    name: str = "cosine"
    warmup_steps: int = 0
    warmup_ratio: float = 0.0
    total_steps: int = 1000


@dataclass
class DataConfig:
    """Dataset configuration."""
    path: str = ""
    name: str = ""
    split: str = "train"
    max_length: int = 512
    batch_size: int = 8
    num_workers: int = 0
    shuffle: bool = True
    streaming: bool = False
    subset: Optional[float] = None
    seed: int = 42


@dataclass
class ModelConfig:
    """Model architecture configuration."""
    name_or_path: str = "gpt2"
    model_type: str = "causal_lm"
    num_layers: Optional[int] = None
    hidden_size: Optional[int] = None
    num_attention_heads: Optional[int] = None
    intermediate_size: Optional[int] = None
    max_position_embeddings: Optional[int] = None
    vocab_size: Optional[int] = None
    torch_dtype: str = "float32"
    device_map: str = "auto"
    load_in_8bit: bool = False
    load_in_4bit: bool = False


@dataclass
class TrainingConfig:
    """Full training configuration."""
    model: ModelConfig = field(default_factory=ModelConfig)
    optimizer: OptimizerConfig = field(default_factory=OptimizerConfig)
    scheduler: SchedulerConfig = field(default_factory=SchedulerConfig)
    data: DataConfig = field(default_factory=DataConfig)
    epochs: int = 1
    max_steps: int = -1
    gradient_accumulation_steps: int = 1
    max_grad_norm: float = 1.0
    seed: int = 42
    output_dir: str = "./output"
    logging_steps: int = 10
    eval_steps: int = 500
    save_steps: int = 500
    save_total_limit: int = 2
    fp16: bool = False
    bf16: bool = False
    deepspeed: Optional[str] = None
    fsdp: Optional[str] = None
    lora_r: int = 0
    lora_alpha: int = 32
    lora_dropout: float = 0.1
    lora_target_modules: Optional[List[str]] = None
    do_train: bool = True
    do_eval: bool = True
    do_predict: bool = True
    remove_unused_columns: bool = True
    report_to: List[str] = field(default_factory=lambda: ["tensorboard"])

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TrainingConfig":
        """Build config from a dictionary."""
        return cls(**data)

    @classmethod
    def from_yaml(cls, path: str) -> "TrainingConfig":
        """Load configuration from a YAML file."""
        if yaml is None:
            raise ImportError("PyYAML is not installed. Install with: pip install pyyaml")
        with open(path, "r") as f:
            data = yaml.safe_load(f)
        return cls.from_dict(data)


@dataclass
class ExperimentConfig:
    """Configuration for a named experiment."""
    name: str
    config: TrainingConfig = field(default_factory=TrainingConfig)
    description: str = ""
    tags: List[str] = field(default_factory=list)
    priority: str = "normal"
    distributed: bool = False
    num_processes: int = 1
    num_devices_per_process: int = 1
    created_at: float = field(default_factory=lambda: __import__("time").time())
