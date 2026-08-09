# Copyright (c) Ultrone Contributors. All rights reserved.
"""Long-context reasoning for frontier models.

Implements the document → chunking → embedding → retrieval → compression →
LLM pipeline for handling extremely long documents without putting every
token into the model context. Measures retrieval recall, context
utilization, latency, token count, memory usage, and answer accuracy.
"""

from __future__ import annotations

import hashlib
import logging
import math
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple

logger = logging.getLogger("Ultrone.Frontier.Model.LongContext")


@dataclass
class Chunk:
    """A chunk of a document."""

    text: str
    index: int
    start_char: int
    end_char: int
    embedding: Optional[List[float]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "index": self.index,
            "start_char": self.start_char,
            "end_char": self.end_char,
            "text": self.text,
            "metadata": self.metadata,
        }


@dataclass
class LongContextResult:
    """The result of long-context processing."""

    answer: str = ""
    chunks_retrieved: List[Chunk] = field(default_factory=list)
    total_chunks: int = 0
    total_tokens: int = 0
    context_tokens: int = 0
    retrieval_recall: float = 0.0
    context_utilization: float = 0.0
    latency_seconds: float = 0.0
    memory_usage_bytes: int = 0
    answer_accuracy: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "answer": self.answer,
            "chunks_retrieved": [c.to_dict() for c in self.chunks_retrieved],
            "total_chunks": self.total_chunks,
            "total_tokens": self.total_tokens,
            "context_tokens": self.context_tokens,
            "retrieval_recall": self.retrieval_recall,
            "context_utilization": self.context_utilization,
            "latency_seconds": self.latency_seconds,
            "memory_usage_bytes": self.memory_usage_bytes,
            "answer_accuracy": self.answer_accuracy,
            "metadata": self.metadata,
        }


class DocumentChunker:
    """Splits documents into overlapping chunks.

    Supports character-based and token-based chunking with configurable
    overlap.
    """

    def __init__(
        self,
        chunk_size: int = 512,
        overlap: int = 64,
        tokenizer: Optional[Callable[[str], List[str]]] = None,
    ):
        self.chunk_size = chunk_size
        self.overlap = overlap
        self.tokenizer = tokenizer or (lambda text: text.split())

    def chunk(self, document: str) -> List[Chunk]:
        """Split a document into chunks."""
        tokens = self.tokenizer(document)
        chunks: List[Chunk] = []
        if not tokens:
            return chunks

        # Reconstruct character offsets
        char_positions: List[int] = []
        pos = 0
        for token in tokens:
            # Find the token in the document starting from pos
            idx = document.find(token, pos)
            if idx == -1:
                idx = pos
            char_positions.append(idx)
            pos = idx + len(token)

        step = max(1, self.chunk_size - self.overlap)
        for i in range(0, len(tokens), step):
            end = min(i + self.chunk_size, len(tokens))
            chunk_tokens = tokens[i:end]
            start_char = char_positions[i] if i < len(char_positions) else 0
            end_char = (
                char_positions[end - 1] + len(tokens[end - 1])
                if end - 1 < len(char_positions)
                else len(document)
            )
            text = document[start_char:end_char]
            chunks.append(
                Chunk(
                    text=text,
                    index=len(chunks),
                    start_char=start_char,
                    end_char=end_char,
                )
            )
            if end >= len(tokens):
                break
        return chunks


class EmbeddingIndex:
    """Simple in-memory embedding index with cosine similarity search."""

    def __init__(self, embedder: Optional[Callable[[str], List[float]]] = None, dim: int = 256):
        self.embedder = embedder
        self.dim = dim
        self._vectors: Dict[int, List[float]] = {}
        self._chunks: Dict[int, Chunk] = {}

    def add(self, chunk: Chunk) -> None:
        """Index a chunk."""
        if self.embedder is not None:
            vec = self.embedder(chunk.text)
            if len(vec) != self.dim:
                if len(vec) > self.dim:
                    vec = vec[: self.dim]
                else:
                    vec = vec + [0.0] * (self.dim - len(vec))
        else:
            vec = self._hash_embed(chunk.text)
        chunk.embedding = vec
        self._vectors[chunk.index] = vec
        self._chunks[chunk.index] = chunk

    def _hash_embed(self, text: str) -> List[float]:
        """Feature-hash embedding fallback."""
        vec = [0.0] * self.dim
        for token in text.lower().split():
            digest = hashlib.md5(token.encode("utf-8")).digest()
            idx = int.from_bytes(digest[:4], "big") % self.dim
            sign = 1.0 if digest[4] % 2 == 0 else -1.0
            vec[idx] += sign
        norm = math.sqrt(sum(v * v for v in vec)) or 1.0
        return [v / norm for v in vec]

    @staticmethod
    def _cosine(a: List[float], b: List[float]) -> float:
        if not a or not b or len(a) != len(b):
            return 0.0
        dot = sum(x * y for x, y in zip(a, b))
        na = math.sqrt(sum(x * x for x in a))
        nb = math.sqrt(sum(y * y for y in b))
        if na == 0.0 or nb == 0.0:
            return 0.0
        return dot / (na * nb)

    def search(self, query: str, top_k: int = 5) -> List[Tuple[Chunk, float]]:
        """Search for the most similar chunks to a query."""
        if self.embedder is not None:
            q_vec = self.embedder(query)
            if len(q_vec) != self.dim:
                if len(q_vec) > self.dim:
                    q_vec = q_vec[: self.dim]
                else:
                    q_vec = q_vec + [0.0] * (self.dim - len(q_vec))
        else:
            q_vec = self._hash_embed(query)

        results = []
        for idx, vec in self._vectors.items():
            score = self._cosine(q_vec, vec)
            results.append((self._chunks[idx], score))
        results.sort(key=lambda x: x[1], reverse=True)
        return results[:top_k]

    def __len__(self) -> int:
        return len(self._vectors)


class ContextCompressor:
    """Compresses retrieved context to fit within a token budget.

    Uses extractive summarization: keeps the most informative sentences
    based on keyword overlap with the query.
    """

    def __init__(self, max_tokens: int = 1024, tokenizer: Optional[Callable[[str], List[str]]] = None):
        self.max_tokens = max_tokens
        self.tokenizer = tokenizer or (lambda text: text.split())

    def compress(self, chunks: List[Chunk], query: str) -> str:
        """Compress a list of chunks into a context string."""
        query_tokens = set(self.tokenizer(query.lower()))
        sentences: List[Tuple[str, float]] = []

        for chunk in chunks:
            for sent in chunk.text.replace("\n", " ").split(". "):
                sent = sent.strip()
                if not sent:
                    continue
                sent_tokens = self.tokenizer(sent.lower())
                overlap = len(query_tokens & set(sent_tokens))
                score = overlap / (len(sent_tokens) + 1)
                sentences.append((sent, score))

        # Sort by score, then greedily add until token budget
        sentences.sort(key=lambda x: x[1], reverse=True)
        context = ""
        used_tokens = 0
        for sent, _ in sentences:
            sent_tokens = self.tokenizer(sent)
            if used_tokens + len(sent_tokens) > self.max_tokens:
                break
            context += sent + ". "
            used_tokens += len(sent_tokens)

        return context.strip()


class LongContextEngine:
    """End-to-end long-context processing engine.

    Pipeline:
        document → chunking → embedding → retrieval → compression → LLM

    Measures retrieval recall, context utilization, latency, token count,
    memory usage, and answer accuracy.
    """

    def __init__(
        self,
        chunker: Optional[DocumentChunker] = None,
        index: Optional[EmbeddingIndex] = None,
        compressor: Optional[ContextCompressor] = None,
        generator: Optional[Callable[[str], str]] = None,
        tokenizer: Optional[Callable[[str], List[str]]] = None,
    ):
        self.chunker = chunker or DocumentChunker()
        self.index = index or EmbeddingIndex()
        self.compressor = compressor or ContextCompressor()
        self.generator = generator
        self.tokenizer = tokenizer or (lambda text: text.split())
        self._documents: Dict[str, List[Chunk]] = {}
        self._history: List[LongContextResult] = []

    def index_document(self, doc_id: str, document: str) -> int:
        """Index a document. Returns number of chunks."""
        chunks = self.chunker.chunk(document)
        for chunk in chunks:
            self.index.add(chunk)
        self._documents[doc_id] = chunks
        return len(chunks)

    def index_documents(self, documents: Dict[str, str]) -> Dict[str, int]:
        """Index multiple documents. Returns {doc_id: num_chunks}."""
        return {doc_id: self.index_document(doc_id, doc) for doc_id, doc in documents.items()}

    def process(
        self,
        query: str,
        top_k: int = 5,
        expected_answer: Optional[str] = None,
        system_prompt: Optional[str] = None,
    ) -> LongContextResult:
        """Process a query against the indexed documents.

        Parameters
        ----------
        query : str
            The question to answer.
        top_k : int
            Number of chunks to retrieve.
        expected_answer : Optional[str]
            Ground-truth answer for accuracy measurement.
        system_prompt : Optional[str]
            System prompt for the generator.

        Returns
        -------
        LongContextResult
            The result with all metrics.
        """
        start = time.time()
        result = LongContextResult()

        # 1. Retrieve relevant chunks
        retrieved = self.index.search(query, top_k=top_k)
        result.chunks_retrieved = [c for c, _ in retrieved]
        result.total_chunks = len(self.index)

        # 2. Compress context
        context = self.compressor.compress(result.chunks_retrieved, query)
        result.context_tokens = len(self.tokenizer(context))
        result.total_tokens = sum(len(self.tokenizer(c.text)) for c in result.chunks_retrieved)

        # 3. Generate answer
        if self.generator is not None:
            prompt = ""
            if system_prompt:
                prompt += f"{system_prompt}\n\n"
            prompt += f"Query: {query}\n\nContext:\n{context}\n\nAnswer:"
            try:
                result.answer = self.generator(prompt)
            except Exception as exc:
                logger.error("Long-context generation error: %s", exc)
                result.answer = context
        else:
            result.answer = context

        # 4. Metrics
        result.latency_seconds = time.time() - start
        result.context_utilization = (
            result.context_tokens / result.total_tokens if result.total_tokens > 0 else 0.0
        )
        result.memory_usage_bytes = self._estimate_memory()

        # 5. Accuracy (if expected answer provided)
        if expected_answer:
            result.answer_accuracy = self._compute_accuracy(result.answer, expected_answer)
            result.retrieval_recall = self._compute_recall(result.chunks_retrieved, expected_answer)

        self._history.append(result)
        return result

    def _compute_accuracy(self, answer: str, expected: str) -> float:
        """Compute answer accuracy via token overlap (F1-style)."""
        a_tokens = set(self.tokenizer(answer.lower()))
        e_tokens = set(self.tokenizer(expected.lower()))
        if not e_tokens:
            return 0.0
        overlap = len(a_tokens & e_tokens)
        precision = overlap / len(a_tokens) if a_tokens else 0.0
        recall = overlap / len(e_tokens)
        if precision + recall == 0:
            return 0.0
        return 2 * precision * recall / (precision + recall)

    def _compute_recall(self, chunks: List[Chunk], expected: str) -> float:
        """Compute retrieval recall: fraction of expected tokens in retrieved chunks."""
        e_tokens = set(self.tokenizer(expected.lower()))
        if not e_tokens:
            return 0.0
        chunk_text = " ".join(c.text.lower() for c in chunks)
        c_tokens = set(self.tokenizer(chunk_text))
        return len(e_tokens & c_tokens) / len(e_tokens)

    def _estimate_memory(self) -> int:
        """Estimate memory usage of the index in bytes."""
        total = 0
        for vec in self.index._vectors.values():
            total += len(vec) * 8  # 8 bytes per float
        for chunks in self._documents.values():
            for c in chunks:
                total += len(c.text.encode("utf-8"))
        return total

    def get_history(self) -> List[LongContextResult]:
        """Return all processing results."""
        return list(self._history)

    def get_stats(self) -> Dict[str, Any]:
        """Return engine statistics."""
        if not self._history:
            return {
                "type": "LongContextEngine",
                "documents": len(self._documents),
                "chunks": len(self.index),
                "queries": 0,
            }
        return {
            "type": "LongContextEngine",
            "documents": len(self._documents),
            "chunks": len(self.index),
            "queries": len(self._history),
            "avg_latency": sum(r.latency_seconds for r in self._history) / len(self._history),
            "avg_context_utilization": sum(r.context_utilization for r in self._history) / len(self._history),
            "avg_accuracy": sum(r.answer_accuracy for r in self._history) / len(self._history),
        }