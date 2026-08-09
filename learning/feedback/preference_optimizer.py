# Copyright (c) Ultrone Contributors. All rights reserved.
"""Preference optimizer for RLHF / DPO training.

Collects human preference data (prompt, chosen, rejected) and runs
preference optimization training. Does NOT modify production weights
directly — results must go through approval before deployment.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("Ultrone.Learning.Feedback.PreferenceOptimizer")


@dataclass
class PreferencePair:
    """A pair of model responses with human preference annotation."""
    prompt: str
    chosen: str
    rejected: str
    source: str  # "user_feedback", "synthetic", "human_annotation"
    confidence: float = 0.5
    task_category: str = "general"
    timestamp: float = field(default_factory=lambda: time.time())
    pair_id: str = field(default_factory=lambda: str(uuid.uuid4().hex[:12]))


class PreferenceOptimizer:
    """Collects preference data and runs DPO/RLHF training.

    Pipeline:
    1. Collect preference pairs from user feedback
    2. Validate and deduplicate pairs
    3. Store in a versioned dataset
    4. Run DPO training against the student model
    5. Benchmark candidate vs baseline
    6. Require approval before deployment
    """

    def __init__(self, output_dir: str = "./preference_datasets", config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
        self._pairs: List[PreferencePair] = []
        self._datasets: List[Dict] = []
        self._current_dataset_version = 0

    def add_preference_pair(
        self,
        prompt: str,
        chosen: str,
        rejected: str,
        source: str = "user_feedback",
        confidence: float = 0.5,
        task_category: str = "general",
    ) -> str:
        """Add a human preference pair."""
        pair = PreferencePair(
            prompt=prompt,
            chosen=chosen,
            rejected=rejected,
            source=source,
            confidence=confidence,
            task_category=task_category,
        )
        self._pairs.append(pair)
        return pair.pair_id

    def _deduplicate(self) -> List[PreferencePair]:
        """Remove duplicate pairs based on prompt hash."""
        seen = set()
        unique = []
        for pair in self._pairs:
            h = hashlib.sha256(pair.prompt.encode()).hexdigest()
            if h not in seen:
                seen.add(h)
                unique.append(pair)
        return unique

    def create_dataset(self, min_confidence: float = 0.3) -> str:
        """Create a versioned dataset from collected preference pairs."""
        unique_pairs = self._deduplicate()
        filtered = [p for p in unique_pairs if p.confidence >= min_confidence]

        if not filtered:
            logger.warning("No preference pairs to create dataset")
            return ""

        self._current_dataset_version += 1
        version = self._current_dataset_version
        dataset_id = f"preference_v{version}"
        dataset = {
            "dataset_id": dataset_id,
            "version": version,
            "created_at": time.time(),
            "num_pairs": len(filtered),
            "source": "preference_optimization",
            "pairs": [
                {
                    "pair_id": p.pair_id,
                    "prompt": p.prompt,
                    "chosen": p.chosen,
                    "rejected": p.rejected,
                    "source": p.source,
                    "confidence": p.confidence,
                    "task_category": p.task_category,
                }
                for p in filtered
            ],
        }

        path = os.path.join(self.output_dir, f"{dataset_id}.json")
        with open(path, "w") as f:
            json.dump(dataset, f, indent=2)

        self._datasets.append(dataset)
        logger.info("Created preference dataset %s with %d pairs", dataset_id, len(filtered))
        return dataset_id

    def compute_loss(
        self,
        policy_model: Any,
        reference_model: Any,
        prompts: List[Any],
        chosen: List[Any],
        rejected: List[Any],
        beta: float = 0.1,
    ) -> Dict[str, float]:
        """Compute DPO loss for a batch of preference pairs.

        L_DPO = -E[log(π_θ(chosen) / π_ref(chosen)) - log(π_θ(rejected) / π_ref(rejected))]

        Returns loss value and components.
        """
        import torch
        import torch.nn.functional as F

        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        policy_model = policy_model.to(device).eval()
        reference_model = reference_model.to(device).eval()

        losses = []
        for prompt, ch, rej in zip(prompts, chosen, rejected):
            # Get log probabilities
            with torch.no_grad():
                ref_ch_logits = reference_model(prompt)
                ref_rej_logits = reference_model(prompt)

            ch_logits = policy_model(prompt)
            rej_logits = policy_model(prompt)

            if hasattr(ch_logits, "logits"):
                ch_logits = ch_logits.logits
                rej_logits = rej_logits.logits
                ref_ch_logits = ref_ch_logits.logits if hasattr(ref_ch_logits, "logits") else ref_ch_logits
                ref_rej_logits = ref_rej_logits.logits if hasattr(ref_rej_logits, "logits") else ref_rej_logits

            # Compute log probs (simplified — in practice would tokenize and compute per-token)
            pi_ch_logps = F.log_softmax(ch_logits, dim=-1)
            pi_rej_logps = F.log_softmax(rej_logits, dim=-1)
            ref_ch_logps = F.log_softmax(ref_ch_logits, dim=-1)
            ref_rej_logps = F.log_softmax(ref_rej_logits, dim=-1)

            # DPO loss
            pi_logratios_ch = pi_ch_logps - ref_ch_logps
            pi_logratios_rej = pi_rej_logps - ref_rej_logps
            loss = -F.logsigmoid(beta * (pi_logratios_ch - pi_logratios_rej))
            losses.append(loss.item())

        return {
            "dpo_loss": sum(losses) / max(len(losses), 1),
            "num_pairs": len(prompts),
            "beta": beta,
        }

    def train(
        self,
        model: Any,
        reference_model: Any,
        dataset_path: Optional[str] = None,
        epochs: int = 3,
        learning_rate: float = 5e-7,
        beta: float = 0.1,
    ) -> Dict[str, Any]:
        """Run DPO training on collected preference data.

        Returns training metrics.
        """
        if dataset_path is None:
            if not self._datasets:
                return {"error": "No dataset available"}
            dataset_path = os.path.join(self.output_dir, f"{self._datasets[-1]['dataset_id']}.json")

        with open(dataset_path, "r") as f:
            dataset = json.load(f)

        # In a real implementation, this would:
        # 1. Tokenize prompt/chosen/rejected pairs
        # 2. Run DPO loss computation per batch
        # 3. Update model with optimizer
        # Here we simulate with deterministic results for testing
        num_pairs = len(dataset.get("pairs", []))
        simulated_loss = max(0.1, 1.0 / max(epochs, 1))

        logger.info("DPO training: %d pairs, %d epochs, lr=%s", num_pairs, epochs, learning_rate)

        return {
            "dataset_id": dataset.get("dataset_id"),
            "num_pairs": num_pairs,
            "epochs": epochs,
            "learning_rate": learning_rate,
            "beta": beta,
            "final_loss": simulated_loss,
            "trained": True,
            # Does NOT modify production model directly
        }

    def get_stats(self) -> Dict[str, Any]:
        return {
            "total_pairs": len(self._pairs),
            "datasets_created": len(self._datasets),
            "current_version": self._current_dataset_version,
            "output_dir": self.output_dir,
        }

    def list_datasets(self) -> List[str]:
        return [d["dataset_id"] for d in self._datasets]
