# Copyright (c) Ultrone Contributors. All rights reserved.
"""WorkerSelector for selecting optimal execution workers."""

from __future__ import annotations

import logging
from typing import Dict, List, Optional

from .base_worker import HarnessWorker

logger = logging.getLogger("Ultrone.Harness.Selector")


class WorkerSelector:
    """Selects the best available worker for a given goal or task domain."""

    def __init__(self) -> None:
        self._workers: Dict[str, HarnessWorker] = {}

    def register_worker(self, worker: HarnessWorker) -> None:
        """Register a worker in the pool."""
        self._workers[worker.worker_id] = worker
        logger.debug("Registered worker %s with capabilities %s", worker.worker_id, worker.capabilities)

    def select_worker(
        self,
        domain: Optional[str] = None,
        required_capabilities: Optional[List[str]] = None,
        preferred_id: Optional[str] = None,
    ) -> Optional[HarnessWorker]:
        """Find the most qualified worker for the task."""
        if preferred_id and preferred_id in self._workers:
            return self._workers[preferred_id]

        req_caps = set(c.upper() for c in (required_capabilities or []))

        # Filter by domain if present in worker_id or capabilities
        candidates = list(self._workers.values())
        if domain:
            dom_lower = domain.lower()
            filtered = [w for w in candidates if dom_lower in w.worker_id.lower() or any(dom_lower in c.lower() for c in w.capabilities)]
            if filtered:
                candidates = filtered

        # Filter by capabilities
        for worker in candidates:
            worker_caps = set(c.upper() for c in worker.capabilities)
            if req_caps.issubset(worker_caps):
                return worker

        # Fallback to first candidate if any exist
        return candidates[0] if candidates else None

    def list_workers(self) -> List[HarnessWorker]:
        return list(self._workers.values())
