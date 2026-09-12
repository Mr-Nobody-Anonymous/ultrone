# Copyright (c) Ultrone Contributors. All rights reserved.
"""Frontier Model — unified model abstraction layer.

Provides a complete, configurable model stack for dense Transformers,
Mixture-of-Experts, long-context mechanisms, and inference. Supports local
experimental models and external pretrained models (HuggingFace, vLLM,
llama.cpp).
"""

from __future__ import annotations

from .activation import (
    ActivationFunction,
    get_activation,
    get_activation_from_string,
    ACTIVATION_REGISTRY,
)
from .attention import KVCache, MultiHeadAttention
from .base_model import (
    BaseModel,
    RuleBasedModel,
    MockModel,
    HuggingFaceModel,
    VLLMModel,
    LlamaCppModel,
    create_model,
)
from .decoding import Decoder, DecodingConfig, DecodingResult, SpeculativeDecoder
from .embeddings import (
    EmbeddingModule,
    TokenEmbedding,
    LearnedPositionEmbedding,
    compute_rotary_embeddings,
    apply_rotary_pos_emb,
)
from .expert import Expert
from .inference_engine import InferenceEngine, InferenceRequest, InferenceResult
from .long_context import (
    LongContextEngine,
    DocumentChunker,
    EmbeddingIndex,
    ContextCompressor,
    LongContextResult,
)
from .model_config import (
    ModelConfig,
    AttentionType,
    ActivationType,
    NormType,
    QuantizationType,
    PositionEncodingType,
)
from .model_registry import ModelRegistry, ModelRecord, get_model_registry
from .moe import SparseMoE
from .normalization import get_norm, get_norm_from_string, RMSNorm, LayerNorm, BatchNorm
from .output_head import OutputHead
from .router import MoERouter
from .tokenizer import BPETokenizer, HuggingFaceTokenizerAdapter, get_tokenizer
from .transformer import TransformerModel, TransformerBlock, FeedForward

__all__ = [
    # Config
    "ModelConfig",
    "AttentionType",
    "ActivationType",
    "NormType",
    "QuantizationType",
    "PositionEncodingType",
    # Activation
    "ActivationFunction",
    "get_activation",
    "get_activation_from_string",
    "ACTIVATION_REGISTRY",
    # Attention
    "KVCache",
    "MultiHeadAttention",
    # Base model
    "BaseModel",
    "RuleBasedModel",
    "MockModel",
    "HuggingFaceModel",
    "VLLMModel",
    "LlamaCppModel",
    "create_model",
    # Decoding
    "Decoder",
    "DecodingConfig",
    "DecodingResult",
    "SpeculativeDecoder",
    # Embeddings
    "EmbeddingModule",
    "TokenEmbedding",
    "LearnedPositionEmbedding",
    "compute_rotary_embeddings",
    "apply_rotary_pos_emb",
    # Expert
    "Expert",
    # Inference
    "InferenceEngine",
    "InferenceRequest",
    "InferenceResult",
    # Long context
    "LongContextEngine",
    "DocumentChunker",
    "EmbeddingIndex",
    "ContextCompressor",
    "LongContextResult",
    # Registry
    "ModelRegistry",
    "ModelRecord",
    "get_model_registry",
    # MoE
    "SparseMoE",
    "MoERouter",
    # Normalization
    "get_norm",
    "get_norm_from_string",
    "RMSNorm",
    "LayerNorm",
    "BatchNorm",
    # Output
    "OutputHead",
    # Tokenizer
    "BPETokenizer",
    "HuggingFaceTokenizerAdapter",
    "get_tokenizer",
    # Transformer
    "TransformerModel",
    "TransformerBlock",
    "FeedForward",
]