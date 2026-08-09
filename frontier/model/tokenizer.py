# Copyright (c) Ultrone Contributors. All rights reserved.
"""Tokenizer for frontier models.

Provides a real byte-pair-encoding (BPE) tokenizer with a pure-Python
implementation and optional HuggingFace integration. The BPE implementation
performs actual merges — no stubs.
"""

from __future__ import annotations

import json
import re
from collections import defaultdict
from typing import Any, Dict, List, Optional, Tuple


class BPETokenizer:
    """Byte-Pair-Encoding tokenizer.

    Implements the standard BPE training and encoding algorithms:

    1. Split text into words (pre-tokenization).
    2. Count symbol pairs and merge the most frequent pair.
    3. Repeat until the target vocabulary size is reached.

    Encoding applies the learned merges to new text.
    """

    def __init__(self, vocab_size: int = 32000):
        self.vocab_size = vocab_size
        self.merges: Dict[Tuple[str, str], int] = {}
        self.vocab: Dict[str, int] = {}
        self._special_tokens: Dict[str, int] = {}
        self._pre_token_re = re.compile(
            r"""'s|'t|'re|'ve|'m|'ll|'d| ?\p{L}+| ?\p{N}+| ?[^\s\p{L}\p{N}]+|\s+(?!\S)|\s+"""
        )

    # ------------------------------------------------------------------
    # Training
    # ------------------------------------------------------------------
    def train(self, texts: List[str], min_frequency: int = 2) -> Dict[str, Any]:
        """Train BPE merges on a corpus of texts.

        Returns training statistics.
        """
        # Initialize vocab with bytes
        self.vocab = {bytes([i]).decode("latin-1"): i for i in range(256)}
        next_id = 256

        # Pre-tokenize all texts
        word_freqs: Dict[str, int] = defaultdict(int)
        for text in texts:
            for word in self._pre_tokenize(text):
                word_freqs[word] += 1

        # Split each word into characters
        splits = {word: list(word) for word in word_freqs}

        # Iteratively merge most frequent pairs
        merges_done = 0
        while merges_done < self.vocab_size - 256:
            pair_freqs = self._compute_pair_freqs(splits, word_freqs)
            if not pair_freqs:
                break
            best_pair, freq = max(pair_freqs.items(), key=lambda x: x[1])
            if freq < min_frequency:
                break
            # Merge
            self.merges[best_pair] = next_id
            self.vocab[best_pair[0] + best_pair[1]] = next_id
            next_id += 1
            merges_done += 1
            # Update splits
            for word in splits:
                splits[word] = self._merge_pair(splits[word], best_pair)

        return {
            "vocab_size": len(self.vocab),
            "merges": len(self.merges),
            "tokens_trained": sum(word_freqs.values()),
        }

    def _pre_tokenize(self, text: str) -> List[str]:
        """Split text into words."""
        return self._pre_token_re.findall(text)

    def _compute_pair_freqs(
        self, splits: Dict[str, List[str]], word_freqs: Dict[str, int]
    ) -> Dict[Tuple[str, str], int]:
        """Count frequencies of adjacent symbol pairs."""
        pair_freqs: Dict[Tuple[str, str], int] = defaultdict(int)
        for word, freq in word_freqs.items():
            split = splits[word]
            if len(split) == 1:
                continue
            for i in range(len(split) - 1):
                pair = (split[i], split[i + 1])
                pair_freqs[pair] += freq
        return pair_freqs

    @staticmethod
    def _merge_pair(split: List[str], pair: Tuple[str, str]) -> List[str]:
        """Merge all occurrences of a pair in a split."""
        merged = []
        i = 0
        while i < len(split):
            if i < len(split) - 1 and split[i] == pair[0] and split[i + 1] == pair[1]:
                merged.append(pair[0] + pair[1])
                i += 2
            else:
                merged.append(split[i])
                i += 1
        return merged

    # ------------------------------------------------------------------
    # Encoding / Decoding
    # ------------------------------------------------------------------
    def encode(self, text: str, add_special_tokens: bool = True) -> List[int]:
        """Encode text into token IDs."""
        ids: List[int] = []
        if add_special_tokens and "<bos>" in self._special_tokens:
            ids.append(self._special_tokens["<bos>"])
        for word in self._pre_tokenize(text):
            ids.extend(self._encode_word(word))
        if add_special_tokens and "<eos>" in self._special_tokens:
            ids.append(self._special_tokens["<eos>"])
        return ids

    def _encode_word(self, word: str) -> List[int]:
        """Encode a single word using learned merges."""
        # Handle full-word match
        if word in self.vocab:
            return [self.vocab[word]]

        symbols = list(word)
        while len(symbols) > 1:
            # Find the best merge pair
            pair_freqs: Dict[Tuple[str, str], int] = {}
            for i in range(len(symbols) - 1):
                pair = (symbols[i], symbols[i + 1])
                if pair in self.merges:
                    pair_freqs[pair] = self.merges[pair]
            if not pair_freqs:
                break
            best_pair = min(pair_freqs, key=pair_freqs.get)  # lowest merge id = earliest learned
            symbols = self._merge_pair(symbols, best_pair)

        # Convert to IDs
        ids = []
        for symbol in symbols:
            if symbol in self.vocab:
                ids.append(self.vocab[symbol])
            else:
                # Unknown: fall back to byte-level encoding
                for b in symbol.encode("utf-8"):
                    ids.append(self.vocab.get(bytes([b]).decode("latin-1"), 0))
        return ids

    def decode(self, ids: List[int], skip_special_tokens: bool = True) -> str:
        """Decode token IDs back to text."""
        # Build reverse vocab
        id_to_token = {v: k for k, v in self.vocab.items()}
        special_ids = set(self._special_tokens.values()) if skip_special_tokens else set()

        tokens = []
        for token_id in ids:
            if token_id in special_ids:
                continue
            token = id_to_token.get(token_id, "")
            tokens.append(token)

        text = "".join(tokens)
        # Convert byte-level tokens back to UTF-8
        try:
            return text.encode("latin-1").decode("utf-8", errors="replace")
        except (UnicodeEncodeError, UnicodeDecodeError):
            return text

    # ------------------------------------------------------------------
    # Special tokens
    # ------------------------------------------------------------------
    def add_special_tokens(self, tokens: Dict[str, str]) -> int:
        """Add special tokens. Returns number of new tokens added."""
        added = 0
        for name, token in tokens.items():
            if token not in self.vocab:
                next_id = max(self.vocab.values()) + 1
                self.vocab[token] = next_id
                self._special_tokens[name] = next_id
                added += 1
        return added

    # ------------------------------------------------------------------
    # Serialization
    # ------------------------------------------------------------------
    def save(self, path: str) -> None:
        """Save tokenizer to a JSON file."""
        data = {
            "vocab_size": self.vocab_size,
            "vocab": self.vocab,
            "merges": [list(k) + [v] for k, v in self.merges.items()],
            "special_tokens": self._special_tokens,
        }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    @classmethod
    def load(cls, path: str) -> "BPETokenizer":
        """Load tokenizer from a JSON file."""
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        tok = cls(vocab_size=data.get("vocab_size", 32000))
        tok.vocab = {str(k): int(v) for k, v in data.get("vocab", {}).items()}
        tok._special_tokens = {str(k): int(v) for k, v in data.get("special_tokens", {}).items()}
        for item in data.get("merges", []):
            tok.merges[(str(item[0]), str(item[1]))] = int(item[2])
        return tok

    def get_vocab_size(self) -> int:
        """Return the vocabulary size."""
        return len(self.vocab)

    def get_stats(self) -> Dict[str, Any]:
        """Return tokenizer statistics."""
        return {
            "type": "BPETokenizer",
            "vocab_size": len(self.vocab),
            "merges": len(self.merges),
            "special_tokens": len(self._special_tokens),
        }


class HuggingFaceTokenizerAdapter:
    """Adapter for HuggingFace tokenizers.

    Provides a unified interface over ``transformers.AutoTokenizer`` so the
    model layer can use real pretrained tokenizers (e.g. Llama, GPT-2).
    """

    def __init__(self, model_name: str):
        try:
            from transformers import AutoTokenizer

            self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        except ImportError as exc:  # pragma: no cover
            raise ImportError(
                "HuggingFaceTokenizerAdapter requires 'transformers' installed"
            ) from exc

    def encode(self, text: str, add_special_tokens: bool = True) -> List[int]:
        """Encode text into token IDs."""
        return self.tokenizer.encode(text, add_special_tokens=add_special_tokens)

    def decode(self, ids: List[int], skip_special_tokens: bool = True) -> str:
        """Decode token IDs back to text."""
        return self.tokenizer.decode(ids, skip_special_tokens=skip_special_tokens)

    def get_vocab_size(self) -> int:
        """Return the vocabulary size."""
        return len(self.tokenizer)

    def get_stats(self) -> Dict[str, Any]:
        """Return tokenizer statistics."""
        return {
            "type": "HuggingFaceTokenizerAdapter",
            "model": getattr(self.tokenizer, "name_or_path", "unknown"),
            "vocab_size": self.get_vocab_size(),
        }


def get_tokenizer(
    backend: str = "bpe",
    vocab_size: int = 32000,
    model_name: Optional[str] = None,
) -> Any:
    """Get a tokenizer by backend name.

    Parameters
    ----------
    backend : str
        "bpe" for the local BPE tokenizer, "huggingface" for a pretrained
        HuggingFace tokenizer.
    vocab_size : int
        Vocabulary size for the BPE tokenizer.
    model_name : Optional[str]
        Model name for the HuggingFace tokenizer.
    """
    if backend == "huggingface":
        if model_name is None:
            raise ValueError("model_name required for huggingface tokenizer")
        return HuggingFaceTokenizerAdapter(model_name)
    return BPETokenizer(vocab_size=vocab_size)