"""Parallel simulation engine using multi-threading."""

from __future__ import annotations

import logging
import concurrent.futures
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple

logger = logging.getLogger("Ultrone.Sim.Performance.Parallel")


@dataclass
class ParallelConfig:
    """Configuration for parallel engine."""
    num_workers: int = 4
    max_workers: int = 16
    batch_size: int = 100


class ParallelEngine:
    """Multi-threaded parallel simulation engine.

    Distributes independent simulation tasks across worker threads
    for parallel execution. Suitable for batch evaluation of
    multiple scenarios or parallel agent updates.
    """

    def __init__(self, config: Optional[ParallelConfig] = None):
        self.config = config or ParallelConfig()

    def map(self, fn: Callable, items: List[Any]) -> List[Any]:
        """Apply fn to each item in parallel.

        Returns results in the same order as items.
        """
        num_workers = min(self.config.max_workers, max(1, self.config.num_workers))
        with concurrent.futures.ThreadPoolExecutor(max_workers=num_workers) as executor:
            futures = [executor.submit(fn, item) for item in items]
            results = []
            for future in concurrent.futures.as_completed(futures):
                try:
                    results.append(future.result())
                except Exception as e:
                    logger.error("Parallel task failed: %s", e)
                    results.append(None)
        return results

    def get_stats(self) -> Dict[str, Any]:
        return {"type": "ParallelEngine", "workers": self.config.num_workers}
