# Copyright (c) Ultrone Contributors. All rights reserved.
"""Contract Net Protocol for task delegation."""

from __future__ import annotations

import logging
import numpy as np
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from .base import BaseCoordinator, CoordinationConfig

logger = logging.getLogger("Ultrone.Brain.Reasoning.Coordination.ContractNet")


@dataclass
class ContractNetConfig(CoordinationConfig):
    """Configuration for Contract Net Protocol."""
    announcement_ttl: int = 3
    max_bids_per_task: int = 5


class ContractNet(BaseCoordinator):
    """Contract Net Protocol implementation.

    Manager announces tasks, contractors bid, manager awards contracts.
    """

    def __init__(self, config: Optional[ContractNetConfig] = None):
        super().__init__(config or ContractNetConfig())

    def coordinate(self, context: Dict[str, Any]) -> Dict[str, Any]:
        tasks = context.get("tasks", [])
        awards = {}
        for task in tasks:
            bids = {aid: np.random.random() for aid in self._agents}
            sorted_bids = sorted(bids.items(), key=lambda x: -x[1])
            awards[task["id"]] = sorted_bids[:self._config.max_bids_per_task]
        return {"awards": awards}

    def get_stats(self) -> Dict[str, Any]:
        return {"type": "ContractNet"}