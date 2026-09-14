# Copyright (c) Ultrone Contributors. All rights reserved.
"""Persistent Checkpoint Store for long-running agent survival across crashes."""

from __future__ import annotations

import json
import logging
import os
import tempfile
from pathlib import Path
from typing import Dict, List, Optional

from .schemas import CheckpointData

logger = logging.getLogger("Ultrone.Harness.Checkpoint")


class CheckpointStore:
    """Atomic file-based and in-memory checkpoint store."""

    def __init__(self, storage_dir: Optional[str] = None) -> None:
        self.storage_dir = Path(storage_dir) if storage_dir else None
        if self.storage_dir:
            self.storage_dir.mkdir(parents=True, exist_ok=True)
        self._memory_store: Dict[str, List[CheckpointData]] = {}

    def save(self, checkpoint: CheckpointData) -> str:
        """Persist a checkpoint snapshot atomically.

        Returns
        -------
        str
            The identifier or path of the saved checkpoint.
        """
        task_id = checkpoint.task_id
        if task_id not in self._memory_store:
            self._memory_store[task_id] = []
        self._memory_store[task_id].append(checkpoint)

        if not self.storage_dir:
            return f"mem://{task_id}/{len(self._memory_store[task_id])}"

        task_dir = self.storage_dir / task_id
        task_dir.mkdir(parents=True, exist_ok=True)

        filename = f"checkpoint_{int(checkpoint.timestamp)}_{checkpoint.current_phase.lower()}.json"
        target_path = task_dir / filename
        latest_path = task_dir / "latest.json"

        # Atomic write pattern: write to tmp file in same directory and rename
        payload = json.dumps(checkpoint.to_dict(), indent=2)
        with tempfile.NamedTemporaryFile("w", dir=task_dir, delete=False, encoding="utf-8") as tmp:
            tmp.write(payload)
            tmp_name = tmp.name

        os.replace(tmp_name, str(target_path))

        # Update latest pointer atomically
        with tempfile.NamedTemporaryFile("w", dir=task_dir, delete=False, encoding="utf-8") as tmp:
            tmp.write(payload)
            tmp_name = tmp.name
        os.replace(tmp_name, str(latest_path))

        logger.info("Saved atomic checkpoint for task %s at %s", task_id, target_path)
        return str(target_path)

    def load_latest(self, task_id: str) -> Optional[CheckpointData]:
        """Load the most recent checkpoint for a task."""
        if self.storage_dir:
            latest_path = self.storage_dir / task_id / "latest.json"
            if latest_path.exists():
                try:
                    with open(latest_path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    return CheckpointData.from_dict(data)
                except Exception as e:
                    logger.error("Failed to read latest checkpoint for %s: %s", task_id, e)

        # Fallback to in-memory store
        history = self._memory_store.get(task_id, [])
        if history:
            return history[-1]
        return None

    def list_checkpoints(self, task_id: str) -> List[CheckpointData]:
        """List all available checkpoints for a task in chronological order."""
        if self.storage_dir:
            task_dir = self.storage_dir / task_id
            if task_dir.exists():
                results: List[CheckpointData] = []
                for p in sorted(task_dir.glob("checkpoint_*.json")):
                    try:
                        with open(p, "r", encoding="utf-8") as f:
                            results.append(CheckpointData.from_dict(json.load(f)))
                    except Exception as e:
                        logger.warning("Skipping corrupted checkpoint file %s: %s", p, e)
                if results:
                    return results

        return list(self._memory_store.get(task_id, []))
