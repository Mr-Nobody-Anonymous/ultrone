# Copyright (c) Ultrone Contributors. All rights reserved.
"""Distributed consensus protocol for multi-agent agreement."""

from __future__ import annotations

import logging
import numpy as np
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from .base import BaseCoordinator, CoordinationConfig

logger = logging.getLogger("Ultrone.Brain.Reasoning.Coordination.Consensus")


@dataclass
class ConsensusConfig(CoordinationConfig):
    """Configuration for consensus protocol."""
    consensus_threshold: float = 0.67
    max_rounds: int = 10
    fault_tolerance: int = 0


class ConsensusProtocol(BaseCoordinator):
    """Distributed consensus protocol for reaching agreement among agents.

    Implements a simplified Byzantine fault-tolerant consensus where
    agents exchange proposals and vote until agreement is reached.
    """

    def __init__(self, config: Optional[ConsensusConfig] = None):
        super().__init__(config or ConsensusConfig())
        self._config: ConsensusConfig = self.config  # type: ignore

    def coordinate(self, context: Dict[str, Any]) -> Dict[str, Any]:
        proposals = context.get("proposals", {})
        if not proposals:
            return {"consensus": False, "agreed_value": None, "rounds": 0}

        for round_num in range(self._config.max_rounds):
            values = list(proposals.values())
            if not values:
                break
            unique, counts = np.unique(values, return_counts=True)
            majority_idx = np.argmax(counts)
            if counts[majority_idx] / len(values) >= self._config.consensus_threshold:
                return {
                    "consensus": True,
                    "agreed_value": unique[majority_idx],
                    "rounds": round_num + 1,
                    "support": float(counts[majority_idx] / len(values)),
                }
            # Simulate vote update
            proposals = {k: np.random.choice(values) for k in proposals}

        return {"consensus": False, "agreed_value": None, "rounds": self._config.max_rounds}

    def get_stats(self) -> Dict[str, Any]:
        return {"type": "ConsensusProtocol", "threshold": self._config.consensus_threshold}