# Copyright (c) Ultrone Contributors. All rights reserved.
"""Decoding strategies for frontier models.

Implements greedy decoding, beam search, top-k sampling, nucleus (top-p)
sampling, and speculative decoding. All strategies operate on a
``next_token_logits`` callable for backend-agnostic use.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple


@dataclass
class DecodingConfig:
    """Configuration for decoding."""

    max_new_tokens: int = 64
    temperature: float = 1.0
    top_k: int = 50
    top_p: float = 0.95
    repetition_penalty: float = 1.0
    do_sample: bool = False
    num_beams: int = 1
    eos_token_id: Optional[int] = None
    pad_token_id: Optional[int] = 0
    seed: int = 42


@dataclass
class DecodingResult:
    """The result of a decoding run."""

    output_ids: List[int]
    scores: List[float] = field(default_factory=list)
    finished: bool = False
    num_tokens: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "output_ids": self.output_ids,
            "scores": self.scores,
            "finished": self.finished,
            "num_tokens": self.num_tokens,
            "metadata": self.metadata,
        }


class Decoder:
    """Decodes token sequences using various strategies.

    Parameters
    ----------
    next_token_logits : Callable
        A callable ``(input_ids) -> logits`` where ``input_ids`` is a list
        of token IDs and ``logits`` is a list of vocab logits.
    config : DecodingConfig
        Decoding configuration.
    """

    def __init__(
        self,
        next_token_logits: Callable[[List[int]], List[float]],
        config: Optional[DecodingConfig] = None,
    ):
        self.next_token_logits = next_token_logits
        self.config = config or DecodingConfig()
        self._rng = random.Random(self.config.seed)

    def decode(self, input_ids: List[int]) -> DecodingResult:
        """Decode a sequence from input_ids.

        Parameters
        ----------
        input_ids : List[int]
            The prompt token IDs.

        Returns
        -------
        DecodingResult
            The generated token IDs and scores.
        """
        if self.config.num_beams > 1:
            return self._beam_search(input_ids)
        return self._greedy_or_sample(input_ids)

    # ------------------------------------------------------------------
    # Greedy / Sampling
    # ------------------------------------------------------------------
    def _greedy_or_sample(self, input_ids: List[int]) -> DecodingResult:
        """Greedy decoding or sampling."""
        output_ids = list(input_ids)
        scores: List[float] = []
        finished = False

        for _ in range(self.config.max_new_tokens):
            logits = self.next_token_logits(output_ids)
            logits = self._apply_repetition_penalty(logits, output_ids)
            logits = self._apply_temperature(logits)

            if self.config.do_sample:
                next_id, score = self._sample(logits)
            else:
                next_id, score = self._greedy(logits)

            scores.append(score)
            output_ids.append(next_id)

            if self.config.eos_token_id is not None and next_id == self.config.eos_token_id:
                finished = True
                break

        return DecodingResult(
            output_ids=output_ids,
            scores=scores,
            finished=finished,
            num_tokens=len(output_ids) - len(input_ids),
        )

    def _greedy(self, logits: List[float]) -> Tuple[int, float]:
        """Greedy token selection."""
        best_idx = 0
        best_val = logits[0]
        for i, val in enumerate(logits[1:], start=1):
            if val > best_val:
                best_val = val
                best_idx = i
        return best_idx, best_val

    def _sample(self, logits: List[float]) -> Tuple[int, float]:
        """Sample a token from logits."""
        # Top-k filtering
        if self.config.top_k > 0 and self.config.top_k < len(logits):
            indices = sorted(range(len(logits)), key=lambda i: logits[i], reverse=True)[: self.config.top_k]
            filtered = [-float("inf")] * len(logits)
            for i in indices:
                filtered[i] = logits[i]
            logits = filtered

        # Top-p (nucleus) filtering
        if self.config.top_p < 1.0:
            logits = self._top_p_filter(logits)

        # Softmax
        probs = self._softmax(logits)

        # Sample
        r = self._rng.random()
        cumulative = 0.0
        for i, p in enumerate(probs):
            cumulative += p
            if r <= cumulative:
                return i, math.log(max(p, 1e-9))
        # Fallback to argmax
        best_idx = max(range(len(probs)), key=lambda i: probs[i])
        return best_idx, math.log(max(probs[best_idx], 1e-9))

    def _top_p_filter(self, logits: List[float]) -> List[float]:
        """Nucleus filtering: keep the smallest set of tokens with cumulative prob >= top_p."""
        # Sort by logit
        sorted_indices = sorted(range(len(logits)), key=lambda i: logits[i], reverse=True)
        sorted_probs = self._softmax([logits[i] for i in sorted_indices])

        cumulative = 0.0
        keep = set()
        for idx, prob in zip(sorted_indices, sorted_probs):
            if cumulative >= self.config.top_p:
                break
            keep.add(idx)
            cumulative += prob

        if not keep:
            keep.add(sorted_indices[0])

        filtered = [-float("inf")] * len(logits)
        for i in keep:
            filtered[i] = logits[i]
        return filtered

    @staticmethod
    def _softmax(logits: List[float]) -> List[float]:
        """Numerically stable softmax."""
        max_v = max(logits)
        exps = [math.exp(v - max_v) for v in logits]
        total = sum(exps) or 1.0
        return [e / total for e in exps]

    def _apply_temperature(self, logits: List[float]) -> List[float]:
        """Apply temperature scaling."""
        if self.config.temperature == 1.0:
            return logits
        return [l / self.config.temperature for l in logits]

    def _apply_repetition_penalty(self, logits: List[float], input_ids: List[int]) -> List[float]:
        """Apply repetition penalty to already-generated tokens."""
        if self.config.repetition_penalty == 1.0:
            return logits
        penalty = self.config.repetition_penalty
        result = list(logits)
        for token_id in input_ids:
            if 0 <= token_id < len(result):
                if result[token_id] > 0:
                    result[token_id] /= penalty
                else:
                    result[token_id] *= penalty
        return result

    # ------------------------------------------------------------------
    # Beam Search
    # ------------------------------------------------------------------
    def _beam_search(self, input_ids: List[int]) -> DecodingResult:
        """Beam search decoding."""
        num_beams = self.config.num_beams
        # Each beam: (sequence, cumulative_log_prob, scores)
        beams: List[Tuple[List[int], float, List[float]]] = [(list(input_ids), 0.0, [])]

        for _ in range(self.config.max_new_tokens):
            candidates: List[Tuple[List[int], float, List[float]]] = []
            for seq, cum_log_prob, scores in beams:
                logits = self.next_token_logits(seq)
                logits = self._apply_repetition_penalty(logits, seq)
                logits = self._apply_temperature(logits)
                probs = self._softmax(logits)

                # Top-k per beam
                top_indices = sorted(range(len(probs)), key=lambda i: probs[i], reverse=True)[: num_beams * 2]
                for idx in top_indices:
                    new_seq = seq + [idx]
                    new_log_prob = cum_log_prob + math.log(max(probs[idx], 1e-9))
                    new_scores = scores + [probs[idx]]
                    candidates.append((new_seq, new_log_prob, new_scores))

            # Keep top beams
            candidates.sort(key=lambda x: x[1], reverse=True)
            beams = candidates[:num_beams]

            # Check if all beams hit EOS
            if self.config.eos_token_id is not None:
                if all(seq[-1] == self.config.eos_token_id for seq, _, _ in beams):
                    break

        best_seq, _, best_scores = beams[0]
        return DecodingResult(
            output_ids=best_seq,
            scores=best_scores,
            finished=best_seq[-1] == self.config.eos_token_id if self.config.eos_token_id else False,
            num_tokens=len(best_seq) - len(input_ids),
            metadata={"num_beams": num_beams},
        )

    def get_stats(self) -> Dict[str, Any]:
        """Return decoder statistics."""
        return {
            "type": "Decoder",
            "max_new_tokens": self.config.max_new_tokens,
            "temperature": self.config.temperature,
            "top_k": self.config.top_k,
            "top_p": self.config.top_p,
            "do_sample": self.config.do_sample,
            "num_beams": self.config.num_beams,
        }


class SpeculativeDecoder:
    """Speculative decoding with a draft model.

    Uses a small draft model to propose tokens, then verifies them with the
    target model. Accepts tokens where the target model agrees, and corrects
    where it disagrees.
    """

    def __init__(
        self,
        target_logits: Callable[[List[int]], List[float]],
        draft_logits: Callable[[List[int]], List[float]],
        num_speculative_tokens: int = 4,
        temperature: float = 1.0,
    ):
        self.target_logits = target_logits
        self.draft_logits = draft_logits
        self.num_speculative_tokens = num_speculative_tokens
        self.temperature = temperature
        self._rng = random.Random(42)
        self.accepted_tokens = 0
        self.total_proposed = 0

    def decode(self, input_ids: List[int], max_new_tokens: int = 64) -> DecodingResult:
        """Decode using speculative decoding."""
        output_ids = list(input_ids)
        scores: List[float] = []
        finished = False

        while len(output_ids) - len(input_ids) < max_new_tokens:
            # 1. Draft proposal
            draft_ids = list(output_ids)
            draft_probs_list = []
            for _ in range(self.num_speculative_tokens):
                logits = self.draft_logits(draft_ids)
                probs = self._softmax(logits)
                next_id = self._sample(probs)
                draft_ids.append(next_id)
                draft_probs_list.append(probs)

            # 2. Target verification
            proposed = draft_ids[len(output_ids):]
            self.total_proposed += len(proposed)

            for i, proposed_id in enumerate(proposed):
                target_logits = self.target_logits(output_ids)
                target_probs = self._softmax(target_logits)
                draft_prob = draft_probs_list[i][proposed_id]
                target_prob = target_probs[proposed_id]

                # Accept with probability min(1, target_prob / draft_prob)
                accept_prob = min(1.0, target_prob / max(draft_prob, 1e-9))
                if self._rng.random() < accept_prob:
                    output_ids.append(proposed_id)
                    scores.append(target_prob)
                    self.accepted_tokens += 1
                    if proposed_id == self.config_eos(output_ids):
                        finished = True
                        break
                else:
                    # Reject: sample from the corrected distribution
                    corrected = self._corrected_distribution(target_probs, draft_probs_list[i], proposed_id)
                    next_id = self._sample(corrected)
                    output_ids.append(next_id)
                    scores.append(target_probs[next_id])
                    break
            else:
                # All proposed tokens accepted
                if len(output_ids) - len(input_ids) >= max_new_tokens:
                    break

        return DecodingResult(
            output_ids=output_ids,
            scores=scores,
            finished=finished,
            num_tokens=len(output_ids) - len(input_ids),
            metadata={
                "accepted_tokens": self.accepted_tokens,
                "total_proposed": self.total_proposed,
                "acceptance_rate": self.accepted_tokens / max(1, self.total_proposed),
            },
        )

    def config_eos(self, ids: List[int]) -> Optional[int]:
        """Placeholder for EOS check — subclasses can override."""
        return None

    @staticmethod
    def _corrected_distribution(target_probs: List[float], draft_probs: List[float], rejected_id: int) -> List[float]:
        """Compute the corrected distribution after rejection.

        P_corrected(i) = max(0, P_target(i) - P_draft(i)) / Z
        """
        corrected = [max(0.0, t - d) for t, d in zip(target_probs, draft_probs)]
        total = sum(corrected)
        if total <= 0:
            # Fall back to target distribution
            return target_probs
        return [c / total for c in corrected]

    @staticmethod
    def _softmax(logits: List[float]) -> List[float]:
        """Numerically stable softmax."""
        max_v = max(logits)
        exps = [math.exp(v - max_v) for v in logits]
        total = sum(exps) or 1.0
        return [e / total for e in exps]

    def _sample(self, probs: List[float]) -> int:
        """Sample from a probability distribution."""
        r = self._rng.random()
        cumulative = 0.0
        for i, p in enumerate(probs):
            cumulative += p
            if r <= cumulative:
                return i
        return max(range(len(probs)), key=lambda i: probs[i])

    def get_stats(self) -> Dict[str, Any]:
        """Return speculative decoder statistics."""
        return {
            "type": "SpeculativeDecoder",
            "num_speculative_tokens": self.num_speculative_tokens,
            "accepted_tokens": self.accepted_tokens,
            "total_proposed": self.total_proposed,
            "acceptance_rate": self.accepted_tokens / max(1, self.total_proposed),
        }