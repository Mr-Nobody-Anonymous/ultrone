# Copyright (c) Ultrone Contributors. All rights reserved.
"""Model configuration — typed configuration for frontier models.

Defines the full configuration surface for dense Transformers, Mixture-of-
Experts, long-context mechanisms, quantization, and inference. Configurations
are validated on construction so misconfiguration fails fast.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class AttentionType(Enum):
    """Supported attention mechanisms."""

    FULL = "full"
    SLIDING_WINDOW = "sliding_window"
    CHUNKED = "chunked"
    LINEAR = "linear"
    SPARSE = "sparse"


class ActivationType(Enum):
    """Supported activation functions."""

    GELU = "gelu"
    RELU = "relu"
    SILU = "silu"
    SWISH = "swish"
    MISH = "mish"
    TANH = "tanh"
    QUICK_GELU = "quick_gelu"


class NormType(Enum):
    """Supported normalization layers."""

    LAYER_NORM = "layer_norm"
    RMS_NORM = "rms_norm"
    BATCH_NORM = "batch_norm"


class QuantizationType(Enum):
    """Supported quantization schemes."""

    NONE = "none"
    INT8 = "int8"
    INT4 = "int4"
    FP8 = "fp8"


class PositionEncodingType(Enum):
    """Supported position encodings."""

    LEARNED = "learned"
    ROTARY = "rotary"
    ALIBI = "alibi"
    NONE = "none"


@dataclass
class ModelConfig:
    """Configuration for a frontier model.

    Parameters
    ----------
    vocab_size : int
        Vocabulary size.
    hidden_size : int
        Hidden dimension.
    num_hidden_layers : int
        Number of transformer layers.
    num_attention_heads : int
        Number of attention heads.
    num_key_value_heads : int
        Number of KV heads (for grouped-query attention). Defaults to
        ``num_attention_heads``.
    intermediate_size : int
        FFN hidden dimension.
    max_position_embeddings : int
        Maximum sequence length.
    attention_type : AttentionType
        Attention mechanism.
    window_size : Optional[int]
        Sliding-window size (for ``SLIDING_WINDOW``).
    chunk_size : Optional[int]
        Chunk size (for ``CHUNKED``).
    activation : ActivationType
        Activation function.
    norm_type : NormType
        Normalization layer.
    position_encoding : PositionEncodingType
        Position encoding.
    rope_theta : float
        Rotary base frequency.
    dropout : float
        Dropout probability.
    layer_norm_eps : float
        Epsilon for normalization.
    use_bias : bool
        Whether to use bias in linear layers.
    tie_word_embeddings : bool
        Tie input/output embeddings.
    initializer_range : float
        Std of parameter initialization.
    num_experts : int
        Number of MoE experts (0 = dense).
    num_experts_per_tok : int
        Top-k experts per token.
    expert_capacity_factor : float
        Expert capacity multiplier.
    shared_experts : int
        Number of shared experts.
    aux_loss_coef : float
        Load-balancing auxiliary loss coefficient.
    quantization : QuantizationType
        Quantization scheme.
    use_cache : bool
        Whether to use KV cache.
    use_flash_attention : bool
        Whether to use flash attention (if available).
    torch_dtype : str
        Torch dtype string ("float32", "float16", "bfloat16").
    device : str
        Device ("cpu", "cuda", "mps").
    seed : int
        Random seed.
    """

    # Core dimensions
    vocab_size: int = 32000
    hidden_size: int = 768
    num_hidden_layers: int = 12
    num_attention_heads: int = 12
    num_key_value_heads: Optional[int] = None
    intermediate_size: int = 3072
    max_position_embeddings: int = 2048

    # Attention
    attention_type: AttentionType = AttentionType.FULL
    window_size: Optional[int] = None
    chunk_size: Optional[int] = None

    # Activations / norms
    activation: ActivationType = ActivationType.GELU
    norm_type: NormType = NormType.LAYER_NORM
    position_encoding: PositionEncodingType = PositionEncodingType.LEARNED
    rope_theta: float = 10000.0

    # Regularization
    dropout: float = 0.0
    layer_norm_eps: float = 1e-5
    use_bias: bool = True
    tie_word_embeddings: bool = False
    initializer_range: float = 0.02

    # Mixture of Experts
    num_experts: int = 0
    num_experts_per_tok: int = 2
    expert_capacity_factor: float = 1.25
    shared_experts: int = 0
    aux_loss_coef: float = 0.01

    # Inference
    quantization: QuantizationType = QuantizationType.NONE
    use_cache: bool = True
    use_flash_attention: bool = False
    torch_dtype: str = "float32"
    device: str = "cpu"
    seed: int = 42

    # Extra
    extra: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Validate configuration."""
        if self.vocab_size <= 0:
            raise ValueError("vocab_size must be positive")
        if self.hidden_size <= 0:
            raise ValueError("hidden_size must be positive")
        if self.num_hidden_layers <= 0:
            raise ValueError("num_hidden_layers must be positive")
        if self.num_attention_heads <= 0:
            raise ValueError("num_attention_heads must be positive")
        if self.hidden_size % self.num_attention_heads != 0:
            raise ValueError("hidden_size must be divisible by num_attention_heads")
        if self.num_key_value_heads is None:
            self.num_key_value_heads = self.num_attention_heads
        if self.hidden_size % self.num_key_value_heads != 0:
            raise ValueError("hidden_size must be divisible by num_key_value_heads")
        if self.num_experts < 0:
            raise ValueError("num_experts must be >= 0")
        if self.num_experts > 0 and self.num_experts_per_tok > self.num_experts:
            raise ValueError("num_experts_per_tok must be <= num_experts")
        if self.attention_type == AttentionType.SLIDING_WINDOW and self.window_size is None:
            raise ValueError("window_size required for sliding-window attention")
        if self.attention_type == AttentionType.CHUNKED and self.chunk_size is None:
            raise ValueError("chunk_size required for chunked attention")

    @property
    def head_dim(self) -> int:
        """Dimension per attention head."""
        return self.hidden_size // self.num_attention_heads

    @property
    def is_moe(self) -> bool:
        """Whether this is a Mixture-of-Experts model."""
        return self.num_experts > 0

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to a JSON-compatible dict."""
        return {
            "vocab_size": self.vocab_size,
            "hidden_size": self.hidden_size,
            "num_hidden_layers": self.num_hidden_layers,
            "num_attention_heads": self.num_attention_heads,
            "num_key_value_heads": self.num_key_value_heads,
            "intermediate_size": self.intermediate_size,
            "max_position_embeddings": self.max_position_embeddings,
            "attention_type": self.attention_type.value,
            "window_size": self.window_size,
            "chunk_size": self.chunk_size,
            "activation": self.activation.value,
            "norm_type": self.norm_type.value,
            "position_encoding": self.position_encoding.value,
            "rope_theta": self.rope_theta,
            "dropout": self.dropout,
            "layer_norm_eps": self.layer_norm_eps,
            "use_bias": self.use_bias,
            "tie_word_embeddings": self.tie_word_embeddings,
            "initializer_range": self.initializer_range,
            "num_experts": self.num_experts,
            "num_experts_per_tok": self.num_experts_per_tok,
            "expert_capacity_factor": self.expert_capacity_factor,
            "shared_experts": self.shared_experts,
            "aux_loss_coef": self.aux_loss_coef,
            "quantization": self.quantization.value,
            "use_cache": self.use_cache,
            "use_flash_attention": self.use_flash_attention,
            "torch_dtype": self.torch_dtype,
            "device": self.device,
            "seed": self.seed,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ModelConfig":
        """Deserialize from a dict."""
        known = {k: v for k, v in data.items() if k in cls.__dataclass_fields__}
        # Convert enum strings back to enums
        if "attention_type" in known and isinstance(known["attention_type"], str):
            known["attention_type"] = AttentionType(known["attention_type"])
        if "activation" in known and isinstance(known["activation"], str):
            known["activation"] = ActivationType(known["activation"])
        if "norm_type" in known and isinstance(known["norm_type"], str):
            known["norm_type"] = NormType(known["norm_type"])
        if "position_encoding" in known and isinstance(known["position_encoding"], str):
            known["position_encoding"] = PositionEncodingType(known["position_encoding"])
        if "quantization" in known and isinstance(known["quantization"], str):
            known["quantization"] = QuantizationType(known["quantization"])
        return cls(**known)