# Copyright (c) Ultrone Contributors. All rights reserved.
"""Tokenizer + model pipeline (item 2 of the neural milestone).

Real neural training does not run on raw strings -- it runs on batches
of token ids. This module defines the smallest pipeline that
preserves the four operations a real training/inference loop needs
and that can be exercised end-to-end by tests without downloading
weights:

    1. load()            -- (lazy) build/load the model + tokenizer
    2. tokenize()        -- text -> ``TokenizedExample`` (ids + mask)
    3. batch()           -- list of examples -> ``Batch`` (stacked)
    4. generate_batch()  -- batch -> ``List[GenerationResult]``
    5. save_checkpoint() -- state -> disk (json blob)
    6. load_checkpoint() -- disk -> ``CheckpointLoadResult``

Two implementations live here:

* ``ModelPipeline`` -- protocol-style abstract base that the existing
  ``LocalModelAdapter`` already satisfies. The contract documents what
  a "real" neural pipeline must do.

* ``DeterministicTestPipeline`` -- a fast, dependency-free
  implementation backed by a simple whitespace tokenizer and the
  ``MockNeuralAdapter`` for inference. It is what the tests and the
  standalone benchmark actually run.

The pipeline is *orthogonal* to the orchestration layer: it does not
know about routers, traces, or promotion gates. The LoRA trainer and
the benchmark consume it; nothing in ``orchestration/`` is touched.
"""

from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from self_improvement.neural.adapters import (
    MockNeuralAdapter,
    NeuralAdapterConfig,
    NeuralGenerationStats,
)
from self_improvement.self_training.adapters import ModelOutput


# --- Data types ----------------------------------------------------------- #


@dataclass(frozen=True)
class TokenizerSpec:
    """Tokenizer configuration fingerprint included in the lineage."""

    tokenizer_id: str = "whitespace-v1"
    vocab_size: int = 0
    pad_token_id: int = 0
    eos_token_id: int = 0
    max_length: int = 256

    def __post_init__(self) -> None:
        if self.max_length <= 0:
            raise ValueError("max_length must be positive")
        if self.vocab_size < 0:
            raise ValueError("vocab_size must be non-negative")
        if self.pad_token_id < 0 or self.eos_token_id < 0:
            raise ValueError("token ids must be non-negative")

    def fingerprint(self) -> str:
        payload = {
            "tokenizer_id": self.tokenizer_id,
            "vocab_size": self.vocab_size,
            "pad_token_id": self.pad_token_id,
            "eos_token_id": self.eos_token_id,
            "max_length": self.max_length,
        }
        return hashlib.sha256(
            str(payload).encode("utf-8")).hexdigest()[:16]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "tokenizer_id": self.tokenizer_id,
            "vocab_size": self.vocab_size,
            "pad_token_id": self.pad_token_id,
            "eos_token_id": self.eos_token_id,
            "max_length": self.max_length,
            "fingerprint": self.fingerprint(),
        }


@dataclass
class TokenizedExample:
    """A single tokenized example ready to be batched."""

    example_id: str
    input_ids: List[int]
    attention_mask: List[int]
    label_text: str = ""

    def length(self) -> int:
        return len(self.input_ids)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "example_id": self.example_id,
            "input_ids": list(self.input_ids),
            "attention_mask": list(self.attention_mask),
            "label_text": self.label_text,
        }


@dataclass
class Batch:
    """A padded batch of tokenized examples."""

    example_ids: List[str]
    input_ids: List[List[int]]
    attention_mask: List[List[int]]
    pad_token_id: int

    def size(self) -> int:
        return len(self.example_ids)

    def max_length(self) -> int:
        return max((len(ids) for ids in self.input_ids), default=0)

    def total_tokens(self) -> int:
        return sum(sum(mask) for mask in self.attention_mask)


@dataclass
class GenerationResult:
    """One pipeline emission for one batch element."""

    example_id: str
    output_text: str
    output_token_ids: List[int]
    score: float = 0.0
    stats: Optional[NeuralGenerationStats] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "example_id": self.example_id,
            "output_text": self.output_text,
            "output_token_ids": list(self.output_token_ids),
            "score": round(self.score, 6),
            "stats": self.stats.to_dict() if self.stats else None,
        }


@dataclass
class CheckpointLoadResult:
    """Result of ``load_checkpoint``."""

    path: str
    model_hash: str
    config_fingerprint: str
    extra: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "path": self.path,
            "model_hash": self.model_hash,
            "config_fingerprint": self.config_fingerprint,
            "extra": dict(self.extra),
        }


# --- Abstract pipeline contract ------------------------------------------ #


class ModelPipeline:
    """Protocol-style contract a real model+tokenizer pipeline satisfies.

    The existing ``LocalModelAdapter`` already meets the inference
    half of this contract; a real transformers training loop
    additionally meets the batch + checkpoint half. This class is the
    *documented surface* so a future production implementation has a
    stable target.

    Constructors never perform I/O; the first call to ``load()``
    actually instantiates the model. This keeps adapter construction
    cheap and unit-test-friendly.
    """

    def __init__(self, config: NeuralAdapterConfig,
                 tokenizer: TokenizerSpec) -> None:
        self.config = config
        self.tokenizer_spec = tokenizer
        self._loaded = False

    # -- load / state ---------------------------------------------------- #
    def load(self) -> "ModelPipeline":
        """Materialize the model + tokenizer. May be a no-op for tests."""
        self._loaded = True
        return self

    def is_loaded(self) -> bool:
        return self._loaded

    # -- core ops -------------------------------------------------------- #
    def tokenize(self, example_id: str, text: str, *,
                 label: str = "") -> TokenizedExample:
        raise NotImplementedError

    def batch(self, examples: Sequence[TokenizedExample]) -> Batch:
        raise NotImplementedError

    def generate_batch(self, batch: Batch, *,
                       max_new_tokens: Optional[int] = None
                       ) -> List[GenerationResult]:
        raise NotImplementedError

    # -- checkpoints ----------------------------------------------------- #
    def save_checkpoint(self, path: str) -> str:
        raise NotImplementedError

    def load_checkpoint(self, path: str) -> CheckpointLoadResult:
        raise NotImplementedError


# --- Deterministic whitespace-tokenizer pipeline -------------------------- #


def _whitespace_tokenize(text: str) -> List[str]:
    """Trivial whitespace split -- the deterministic test tokenizer.

    Real deployments swap this for the tokenizer that came with the
    base model (e.g. ``AutoTokenizer.from_pretrained``). The
    abstraction is the same: ``text -> List[int]``.
    """
    return [tok for tok in text.split() if tok]


def _hash_vocab(token_iter: Iterable[str]) -> Dict[str, int]:
    """Stable vocab: deterministic, order-preserving id assignment.

    The id is just the 1-based insertion order. This is not a real
    BPE/SentencePiece vocabulary -- it is a *deterministic* stand-in
    that satisfies the contract (string -> List[int]) without any
    heavy dependencies.
    """
    vocab: Dict[str, int] = {}
    next_id = 1
    for tok in token_iter:
        if tok not in vocab:
            vocab[tok] = next_id
            next_id += 1
    return vocab


class DeterministicTestPipeline(ModelPipeline):
    """A pipeline that does *not* require torch / transformers.

    Tokenization is a stable whitespace + order-preserving vocab;
    inference goes through a ``MockNeuralAdapter`` so a LoRA delta is
    observable in the output. Checkpoints are JSON blobs -- fast,
    human-readable, and the same shape a production pipeline would
    serialize (path, model_hash, config fingerprint, weights).

    This is the implementation the tests and the standalone benchmark
    run; a production deployment would replace only this class, not
    any of the consumers (LoRATrainer, NeuralCapabilityBenchmark).
    """

    def __init__(self, config: NeuralAdapterConfig, *,
                 base_weights: Optional[Dict[str, float]] = None,
                 adapter: Optional[MockNeuralAdapter] = None,
                 extra_vocab: Optional[Sequence[str]] = None,
                 max_length: int = 128) -> None:
        tokenizer = TokenizerSpec(
            tokenizer_id="whitespace-v1",
            pad_token_id=0,
            eos_token_id=0,
            max_length=max_length,
        )
        super().__init__(config=config, tokenizer=tokenizer)
        # Vocab is built lazily on the first tokenize() call so the
        # pipeline can be constructed without scanning any text.
        self._vocab: Dict[str, int] = {}
        self._extra_vocab = list(extra_vocab or [])
        self._adapter = adapter or MockNeuralAdapter(
            config=config, base_weights=base_weights)
        self._base_weights = dict(base_weights or self._adapter.weights())
        self._generation_count = 0

    # -- tokenizer ------------------------------------------------------- #
    def _ensure_vocab(self, text: str) -> None:
        if self._vocab:
            return
        toks = list(self._extra_vocab) + _whitespace_tokenize(text)
        self._vocab = _hash_vocab(toks)
        # Patch the tokenizer spec's reported vocab_size so the
        # lineage reflects the *actual* vocabulary after tokenization.
        self.tokenizer_spec = TokenizerSpec(
            tokenizer_id=self.tokenizer_spec.tokenizer_id,
            vocab_size=max(1, len(self._vocab)),
            pad_token_id=self.tokenizer_spec.pad_token_id,
            eos_token_id=self.tokenizer_spec.eos_token_id,
            max_length=self.tokenizer_spec.max_length,
        )

    def tokenize(self, example_id: str, text: str, *,
                 label: str = "") -> TokenizedExample:
        self._ensure_vocab(text)
        ids: List[int] = []
        for tok in _whitespace_tokenize(text):
            tok_id = self._vocab.get(tok)
            if tok_id is None:
                tok_id = self._vocab[tok] = len(self._vocab) + 1
            ids.append(tok_id)
        # Truncate to max_length so the batch never overflows.
        ids = ids[: self.tokenizer_spec.max_length]
        mask = [1] * len(ids)
        return TokenizedExample(
            example_id=example_id, input_ids=ids,
            attention_mask=mask, label_text=label)

    def batch(self, examples: Sequence[TokenizedExample]) -> Batch:
        if not examples:
            return Batch(example_ids=[], input_ids=[],
                         attention_mask=[],
                         pad_token_id=self.tokenizer_spec.pad_token_id)
        # Right-pad to the longest example in the batch.
        target = max(ex.length() for ex in examples)
        ids: List[List[int]] = []
        masks: List[List[int]] = []
        for ex in examples:
            pad_n = target - ex.length()
            ids.append(list(ex.input_ids)
                       + [self.tokenizer_spec.pad_token_id] * pad_n)
            masks.append(list(ex.attention_mask) + [0] * pad_n)
        return Batch(
            example_ids=[ex.example_id for ex in examples],
            input_ids=ids,
            attention_mask=masks,
            pad_token_id=self.tokenizer_spec.pad_token_id)

    # -- inference ------------------------------------------------------- #
    def _ids_to_text(self, ids: Sequence[int],
                     mask: Sequence[int]) -> str:
        inv = {v: k for k, v in self._vocab.items()}
        tokens: List[str] = []
        for i, m in zip(ids, mask):
            if m and i in inv:
                tokens.append(inv[i])
        return " ".join(tokens)

    def generate_batch(self, batch: Batch, *,
                       max_new_tokens: Optional[int] = None
                       ) -> List[GenerationResult]:
        if not batch.size():
            return []
        results: List[GenerationResult] = []
        for ex_id, ids, mask in zip(batch.example_ids,
                                    batch.input_ids,
                                    batch.attention_mask):
            text = self._ids_to_text(ids, mask)
            output: ModelOutput = self._adapter.generate(text, context="")
            self._generation_count += 1
            stats = (self._adapter.stats()[-1]
                     if self._adapter.stats() else None)
            results.append(GenerationResult(
                example_id=ex_id,
                output_text=output.text,
                output_token_ids=[],  # no real decoder in test pipeline
                score=float(output.meta.get("score", 0.0)),
                stats=stats,
            ))
        return results

    # -- adapter injection (for LoRATrainer) ----------------------------- #
    def set_adapter_delta(self, delta: Dict[str, float]) -> None:
        """Forward a LoRA delta to the underlying adapter."""
        self._adapter.set_adapter_delta(delta)

    def reset_adapter(self) -> None:
        self._adapter.reset_adapter()

    def adapter(self) -> MockNeuralAdapter:
        return self._adapter

    @property
    def generation_count(self) -> int:
        return self._generation_count

    # -- checkpoints ----------------------------------------------------- #
    def save_checkpoint(self, path: str) -> str:
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "kind": "neural_pipeline_v1",
            "config": self.config.to_dict(),
            "tokenizer": self.tokenizer_spec.to_dict(),
            "base_weights": dict(self._base_weights),
            "adapter_delta": dict(self._adapter._state.adapter_delta),
            "model_hash": self._compute_model_hash(),
        }
        target.write_text(json.dumps(payload, sort_keys=True, indent=2),
                          encoding="utf-8")
        return str(target)

    def load_checkpoint(self, path: str) -> CheckpointLoadResult:
        target = Path(path)
        payload = json.loads(target.read_text(encoding="utf-8"))
        if payload.get("kind") != "neural_pipeline_v1":
            raise ValueError(
                f"checkpoint kind {payload.get('kind')!r} is not "
                f"'neural_pipeline_v1'")
        # Restore the adapter delta on the live pipeline.
        delta = payload.get("adapter_delta", {})
        self._adapter.set_adapter_delta(delta)
        return CheckpointLoadResult(
            path=str(target),
            model_hash=payload.get("model_hash", ""),
            config_fingerprint=payload.get("config", {}).get(
                "fingerprint", ""),
            extra={"base_weights": payload.get("base_weights", {}),
                   "tokenizer": payload.get("tokenizer", {}),
                   "adapter_delta": dict(delta)},
        )

    def _compute_model_hash(self) -> str:
        # Stable hash of (config fp, base weights, current adapter
        # delta). Two checkpoints with the same hash represent the
        # exact same trainable state.
        snap = {
            "config_fp": self.config.fingerprint(),
            "base_weights": dict(sorted(self._base_weights.items())),
            "adapter_delta": dict(sorted(
                self._adapter._state.adapter_delta.items())),
        }
        return hashlib.sha256(
            str(snap).encode("utf-8")).hexdigest()[:16]

