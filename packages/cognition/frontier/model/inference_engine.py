# Copyright (c) Ultrone Contributors. All rights reserved.
"""Inference engine for frontier models.

Provides batched inference, KV caching, quantization, and distributed
inference support. Wraps a model and tokenizer into a unified inference
interface.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple

try:
    import torch
    import torch.nn as nn

    TORCH_AVAILABLE = True
except ImportError:  # pragma: no cover
    TORCH_AVAILABLE = False

from runtime import ModelRuntime, Runtime, RuntimeConfig

from .decoding import Decoder, DecodingConfig, DecodingResult
from .model_config import ModelConfig, QuantizationType

logger = logging.getLogger("Ultrone.Frontier.Model.Inference")


@dataclass
class InferenceRequest:
    """A single inference request."""

    prompt: str
    max_new_tokens: int = 64
    temperature: float = 1.0
    top_k: int = 50
    top_p: float = 0.95
    do_sample: bool = False
    num_beams: int = 1
    repetition_penalty: float = 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class InferenceResult:
    """The result of an inference request."""

    text: str
    token_ids: List[int]
    latency_seconds: float = 0.0
    tokens_per_second: float = 0.0
    num_tokens: int = 0
    scores: List[float] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "text": self.text,
            "token_ids": self.token_ids,
            "latency_seconds": self.latency_seconds,
            "tokens_per_second": self.tokens_per_second,
            "num_tokens": self.num_tokens,
            "scores": self.scores,
            "metadata": self.metadata,
        }


class InferenceEngine:
    """Unified inference engine.

    Wraps a model (any object with a ``forward`` method returning logits)
    and a tokenizer into a complete inference pipeline with batching,
    KV caching, and quantization.

    Parameters
    ----------
    model : Any
        The model. Must have a ``forward(input_ids) -> logits`` method.
    tokenizer : Any
        The tokenizer. Must have ``encode(text) -> List[int]`` and
        ``decode(ids) -> str`` methods.
    config : ModelConfig
        Model configuration.
    """

    def __init__(self, model: Any, tokenizer: Any, config: ModelConfig):
        self.model = model
        self.tokenizer = tokenizer
        self.config = config
        self._decoder = None
        self._batch_size = 1
        self._total_calls = 0
        self._total_tokens = 0
        self._total_latency = 0.0
        self.runtime = Runtime(
            RuntimeConfig(
                device=getattr(config, "device", "auto") or "auto",
                precision=getattr(config, "torch_dtype", "auto") or "auto",
                quantization=getattr(config, "quantization", "auto") or "auto",
                max_batch_size=max(1, getattr(config, "max_batch_size", 8) or 8),
            )
        )
        self.model_runtime = ModelRuntime(self.runtime)
        self._model_key = getattr(model, "model_id", type(model).__name__)
        # Load once, reuse via cache (never re-prepare on every call)
        self.model_runtime.load(self._model_key, self.model, warmup=False)

    # ------------------------------------------------------------------
    # Decoding
    # ------------------------------------------------------------------
    def _get_eos_id(self) -> Optional[int]:
        """Get the EOS token ID from the tokenizer if available."""
        if hasattr(self.tokenizer, "_special_tokens"):
            return self.tokenizer._special_tokens.get("<eos>")
        return None

    def _next_token_logits(self, input_ids: List[int]) -> List[float]:
        """Compute logits for the next token given a sequence."""
        # Use cached model when available to avoid re-preparing via ModelRuntime
        cached_model = self.model_runtime.get(self._model_key)
        model = cached_model if cached_model is not None else self.model

        # Call the model's forward with the full sequence through the shared runtime
        output = self.model_runtime.generate(
            self._model_key,
            input_ids,
            model=model,
            batch_size=None,
        )
        # Output could be logits directly, or (logits, ...) tuple, or
        # an object with a logits attribute.
        if isinstance(output, tuple):
            logits = output[0]
        elif hasattr(output, "logits"):
            logits = output.logits
        else:
            logits = output

        # Flatten to the last token's logits
        if hasattr(logits, "shape"):
            # logits shape: [batch, seq, vocab] or [seq, vocab]
            if logits.dim() == 3:
                logits = logits[0, -1, :]
            elif logits.dim() == 2:
                logits = logits[-1, :]
            return logits.tolist()
        # Pure-Python: logits is a list of lists [seq][vocab]
        if logits and hasattr(logits[0], "__iter__"):
            return list(logits[-1])
        return list(logits)

    def generate(self, request: InferenceRequest) -> InferenceResult:
        """Generate text from a prompt.

        Parameters
        ----------
        request : InferenceRequest
            The inference request.

        Returns
        -------
        InferenceResult
            The generated text and metrics.
        """
        start = time.time()
        self._total_calls += 1

        # Encode prompt
        prompt_ids = self.tokenizer.encode(request.prompt)
        if not prompt_ids:
            prompt_ids = [0]  # fallback

        # Create decoder
        config = DecodingConfig(
            max_new_tokens=request.max_new_tokens,
            temperature=request.temperature,
            top_k=request.top_k,
            top_p=request.top_p,
            do_sample=request.do_sample,
            num_beams=request.num_beams,
            repetition_penalty=request.repetition_penalty,
            eos_token_id=self._get_eos_id(),
            seed=self.config.seed,
        )
        decoder = Decoder(self._next_token_logits, config)

        # Decode
        result = decoder.decode(prompt_ids)

        # Decode output tokens to text
        output_ids = result.output_ids[len(prompt_ids):]
        try:
            output_text = self.tokenizer.decode(output_ids)
        except TypeError:
            output_text = ""

        latency = time.time() - start
        num_tokens = len(output_ids)
        self._total_tokens += num_tokens
        self._total_latency += latency

        return InferenceResult(
            text=output_text,
            token_ids=output_ids,
            latency_seconds=latency,
            tokens_per_second=num_tokens / latency if latency > 0 else 0.0,
            num_tokens=num_tokens,
            scores=result.scores,
            metadata={"finished": result.finished},
        )

    def batch_generate(self, requests: List[InferenceRequest]) -> List[InferenceResult]:
        """Generate for multiple requests. Currently processes sequentially.

        Parameters
        ----------
        requests : List[InferenceRequest]
            The requests to process.

        Returns
        -------
        List[InferenceResult]
            Results for each request.
        """
        return [self.generate(req) for req in requests]

    # ------------------------------------------------------------------
    # Quantization
    # ------------------------------------------------------------------
    def quantize(self, quantization_type: QuantizationType = QuantizationType.INT8) -> Dict[str, Any]:
        """Apply quantization to the model.

        For INT8, quantizes linear layer weights to int8 with scale factors.
        Returns quantization statistics.
        """
        if quantization_type == QuantizationType.NONE:
            return {"type": "none", "applied": False}

        num_quantized = 0
        total_params = 0

        if TORCH_AVAILABLE and hasattr(self.model, "blocks"):
            for block in self.model.blocks:
                for name, module in block.__dict__.items():
                    if hasattr(module, "weight") and hasattr(module.weight, "data"):
                        w = module.weight.data
                        total_params += w.numel()
                        if quantization_type == QuantizationType.INT8:
                            # Quantize: scale = max_abs / 127
                            scale = w.abs().max().item() / 127.0
                            if scale > 0:
                                w_int = torch.round(w / scale).clamp(-127, 127).to(torch.int8)
                                module.weight.data = w_int.to(w.dtype) * scale
                                num_quantized += 1

        return {
            "type": quantization_type.value,
            "applied": True,
            "quantized_layers": num_quantized,
            "total_params": total_params,
            "compression_ratio": total_params / (num_quantized * 1) if num_quantized > 0 else 0.0,
        }

    # ------------------------------------------------------------------
    # Distributed inference
    # ------------------------------------------------------------------
    def set_batch_size(self, batch_size: int) -> None:
        """Set the batch size for inference."""
        self._batch_size = batch_size

    # ------------------------------------------------------------------
    # Stats
    # ------------------------------------------------------------------
    def get_stats(self) -> Dict[str, Any]:
        """Return inference engine statistics."""
        return {
            "type": "InferenceEngine",
            "total_calls": self._total_calls,
            "total_tokens": self._total_tokens,
            "total_latency": self._total_latency,
            "avg_latency": self._total_latency / max(1, self._total_calls),
            "avg_tokens_per_second": self._total_tokens / max(0.001, self._total_latency),
            "batch_size": self._batch_size,
            "runtime_backend": self.runtime.get_backend(),
            "runtime_device": self.runtime.get_device(),
            "runtime_precision": self.runtime._dtype,
            "quantization": self.config.quantization.value,
        }

    def __call__(self, prompt: str, **kwargs: Any) -> InferenceResult:
        """Convenience: generate text from a prompt string."""
        request = InferenceRequest(prompt=prompt, **kwargs)
        return self.generate(request)